from __future__ import annotations

import sqlite3
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from vanna.components import (
    ChartComponent,
    DataFrameComponent,
    RichTextComponent,
    StatusCardComponent,
)
from vanna.core.user import RequestContext

from project_utils import (
    DATABASE_PATH,
    chart_type_from_figure,
    configure_logging,
    log_event,
    normalize_question,
    validate_question,
)
from vanna_setup import VannaRuntime, get_agent


class ChatRequest(BaseModel):
    question: str = Field(..., description="Natural language question to convert to SQL.")


class ChatResponse(BaseModel):
    message: str
    sql_query: str
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    chart: dict[str, Any]
    chart_type: str


class HealthResponse(BaseModel):
    status: str
    database: str
    agent_memory_items: int


class ErrorResponse(BaseModel):
    error: str
    detail: str
    code: str


@dataclass(slots=True)
class RateLimitConfig:
    max_requests: int = 30
    window_seconds: int = 60


class SimpleRateLimiter:
    def __init__(self, config: RateLimitConfig | None = None) -> None:
        self.config = config or RateLimitConfig()
        self._requests: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, client_id: str) -> bool:
        now = time.time()
        history = self._requests[client_id]
        while history and now - history[0] > self.config.window_seconds:
            history.popleft()
        if len(history) >= self.config.max_requests:
            return False
        history.append(now)
        return True


class AppState:
    runtime: VannaRuntime | None = None
    cache: dict[str, ChatResponse]
    rate_limiter: SimpleRateLimiter


app_state = AppState()


def error_payload(status_code: int, error: str, detail: str, code: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(error=error, detail=detail, code=code).model_dump(),
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    app_state.cache = {}
    app_state.rate_limiter = SimpleRateLimiter()
    app_state.runtime = await get_agent()
    yield


app = FastAPI(title="Clinic NL2SQL API", version="1.0.0", lifespan=lifespan)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path == "/chat":
        client_id = request.client.host if request.client else "unknown"
        if not app_state.rate_limiter.allow(client_id):
            log_event("rate_limited", client_id=client_id, path=request.url.path)
            return error_payload(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "Rate limit exceeded",
                "Too many requests. Please wait a moment and try again.",
                "rate_limit_exceeded",
            )
    return await call_next(request)


def build_request_context(request: Request) -> RequestContext:
    return RequestContext(
        headers=dict(request.headers),
        cookies=request.cookies,
        remote_addr=request.client.host if request.client else None,
        query_params={key: value for key, value in request.query_params.items()},
        metadata={"path": request.url.path},
    )


async def collect_agent_response(question: str, request_context: RequestContext) -> ChatResponse:
    if app_state.runtime is None:
        raise RuntimeError("Agent runtime is not initialized.")

    sql_query = ""
    message = ""
    columns: list[str] = []
    rows: list[list[Any]] = []
    chart: dict[str, Any] = {}
    chart_type = "none"

    async for component in app_state.runtime.agent.send_message(request_context, question):
        rich_component = component.rich_component
        simple_component = component.simple_component

        if isinstance(rich_component, StatusCardComponent):
            metadata = rich_component.metadata or {}
            if "sql" in metadata:
                sql_query = str(metadata["sql"])

        if isinstance(rich_component, DataFrameComponent):
            columns = list(rich_component.columns)
            rows = [[row.get(column) for column in columns] for row in rich_component.rows]

        if isinstance(rich_component, ChartComponent):
            chart = dict(rich_component.data)
            chart_type = chart_type_from_figure(chart)

        if isinstance(rich_component, RichTextComponent) and rich_component.content.strip():
            message = rich_component.content.strip()
        elif simple_component and getattr(simple_component, "text", "").strip():
            message = str(simple_component.text).strip()

    if not sql_query:
        raise ValueError("The agent did not produce an executable SQL query.")

    if not message:
        message = "Query executed successfully."

    return ChatResponse(
        message=message if rows else "No data found for that question.",
        sql_query=sql_query,
        columns=columns,
        rows=rows,
        row_count=len(rows),
        chart=chart,
        chart_type=chart_type if chart else "none",
    )


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    connection = sqlite3.connect(DATABASE_PATH)
    try:
        connection.execute("SELECT 1").fetchone()
    finally:
        connection.close()

    memory_items = app_state.runtime.seed_count if app_state.runtime else 0
    log_event("health_check", database="connected", agent_memory_items=memory_items)
    return HealthResponse(
        status="ok",
        database="connected",
        agent_memory_items=memory_items,
    )


@app.post(
    "/chat",
    response_model=ChatResponse,
    responses={
        400: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def chat(payload: ChatRequest, request: Request):
    try:
        question = validate_question(payload.question)
    except ValueError as exc:
        return error_payload(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Invalid question",
            str(exc),
            "invalid_question",
        )

    normalized = normalize_question(question)
    client_id = request.client.host if request.client else "unknown"
    log_event("chat_received", client_id=client_id, normalized_question=normalized)

    cached = app_state.cache.get(normalized)
    if cached is not None:
        log_event("cache_hit", normalized_question=normalized)
        return cached

    log_event("cache_miss", normalized_question=normalized)

    try:
        response = await collect_agent_response(question, build_request_context(request))
    except ValueError as exc:
        log_event("chat_validation_error", detail=str(exc))
        return error_payload(
            status.HTTP_400_BAD_REQUEST,
            "Unable to answer question safely",
            str(exc),
            "agent_output_invalid",
        )
    except sqlite3.DatabaseError as exc:
        log_event("database_error", detail=str(exc))
        return error_payload(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Database execution failed",
            "The generated query could not be executed against the database.",
            "database_execution_failed",
        )
    except Exception as exc:
        log_event("chat_runtime_error", detail=str(exc))
        return error_payload(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Internal server error",
            "An unexpected error occurred while processing the question.",
            "internal_server_error",
        )

    app_state.cache[normalized] = response
    log_event(
        "chat_completed",
        normalized_question=normalized,
        row_count=response.row_count,
        chart_type=response.chart_type,
    )
    return response
