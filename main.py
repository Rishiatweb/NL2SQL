from __future__ import annotations

import os
import re
import uuid
import sqlite3
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from google import genai as google_genai
from dotenv import load_dotenv

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from vanna.components import (
    ChartComponent,
    DataFrameComponent,
    NotificationComponent,
    RichTextComponent,
    StatusCardComponent,
)
from vanna.core.user import RequestContext
from vanna.core.tool import ToolContext
from vanna.core.user import User

from project_utils import (
    DATABASE_PATH,
    chart_type_from_figure,
    configure_logging,
    execute_select_sql,
    log_event,
    normalize_question,
    validate_question,
    validate_select_sql,
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
    chart_type: str = Field(
        description="Chart type hint. One of: bar, line, pie, other, none."
    )


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


def extract_sql_from_text(text: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        return ""
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
    match = re.search(r"(SELECT[\s\S]+)", cleaned, re.IGNORECASE)
    if not match:
        return ""
    sql_candidate = match.group(1).strip()
    if "\n\n" in sql_candidate:
        sql_candidate = sql_candidate.split("\n\n", 1)[0].strip()
    return sql_candidate


def get_schema_overview() -> str:
    tables = ["patients", "doctors", "appointments", "treatments", "invoices"]
    connection = sqlite3.connect(DATABASE_PATH)
    try:
        lines: list[str] = []
        for table in tables:
            columns = connection.execute(f"PRAGMA table_info({table})").fetchall()
            column_parts = [f"{col[1]} {col[2]}" for col in columns]
            lines.append(f"{table}({', '.join(column_parts)})")
        return "\n".join(lines)
    finally:
        connection.close()


def generate_sql_directly(question: str, schema: str) -> str:
    """
    Bypass the Vanna agent and call Gemini directly with a SQL-only prompt.
    Used when the agent pipeline fails to produce a tool call.
    Returns a raw SQL string, or "" if generation fails.
    """
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY", "")
    if not api_key:
        return ""

    prompt = (
        "You are a SQL expert. Write a single valid SQLite SELECT query for the question below.\n\n"
        f"Schema:\n{schema}\n\n"
        "Rules:\n"
        "- Return ONLY the SQL query. No explanation. No markdown fences.\n"
        "- Use exact table and column names from the schema.\n"
        "- For dates use SQLite functions: strftime(), julianday(), date(), datetime().\n"
        "- status values — appointments: 'Scheduled','Completed','Cancelled','No-Show'; "
        "invoices: 'Paid','Pending','Overdue'; gender: 'M','F'\n\n"
        f"Question: {question}\n\nSQL:"
    )

    try:
        client = google_genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash", contents=prompt
        )
        sql = response.text.strip()
        # Strip markdown code fences if the model added them
        sql = re.sub(r"^```(?:sql)?\s*", "", sql, flags=re.IGNORECASE)
        sql = re.sub(r"\s*```$", "", sql).strip()
        return sql
    except Exception as exc:
        log_event("direct_sql_generation_failed", error=str(exc))
        return ""


async def build_memory_context(request_context: RequestContext) -> ToolContext:
    if app_state.runtime is None:
        raise RuntimeError("Agent runtime is not initialized.")

    try:
        user = await app_state.runtime.agent.user_resolver.resolve_user(request_context)
    except Exception:
        user = User(id="memory-fallback", group_memberships=["admin"])

    return ToolContext(
        user=user,
        conversation_id="memory-fallback",
        request_id=str(uuid.uuid4()),
        agent_memory=app_state.runtime.agent.agent_memory,
        metadata={"source": "memory_fallback"},
    )


async def memory_fallback_sql(question: str, request_context: RequestContext) -> tuple[str, float]:
    if app_state.runtime is None:
        return "", 0.0

    context = await build_memory_context(request_context)
    results = await app_state.runtime.agent.agent_memory.search_similar_usage(
        question=question,
        context=context,
        limit=1,
        similarity_threshold=0.70,
        tool_name_filter="run_sql",
    )
    if not results:
        return "", 0.0

    memory = results[0].memory
    sql = ""
    if isinstance(memory.args, dict):
        sql = str(memory.args.get("sql", ""))
    return sql, results[0].similarity_score


async def collect_agent_response(question: str, request_context: RequestContext) -> ChatResponse:
    if app_state.runtime is None:
        raise RuntimeError("Agent runtime is not initialized.")

    last_error = ""
    schema_overview = ""

    for attempt in range(2):
        sql_query = ""
        message = ""
        columns: list[str] = []
        rows: list[list[Any]] = []
        chart: dict[str, Any] = {}
        chart_type = "none"
        tool_error = ""

        question_to_send = question
        if attempt > 0:
            if not schema_overview:
                schema_overview = get_schema_overview()
            question_to_send = (
                f"{question}\n\n"
                f"The previous attempt failed with error: {last_error}\n"
                "Use this SQLite schema exactly:\n"
                f"{schema_overview}\n"
                "Return a single valid SELECT query that matches the schema. "
                "If tool calls are not available, respond with ONLY the SQL query."
            )
            log_event("chat_retry", attempt=attempt + 1, reason=last_error)

        async for component in app_state.runtime.agent.send_message(
            request_context, question_to_send
        ):
            rich_component = component.rich_component
            simple_component = component.simple_component

            if isinstance(rich_component, StatusCardComponent):
                metadata = rich_component.metadata or {}
                if "sql" in metadata:
                    sql_query = str(metadata["sql"])

            if isinstance(rich_component, DataFrameComponent):
                columns = list(rich_component.columns)
                rows = [
                    [row.get(column) for column in columns]
                    for row in rich_component.rows
                ]

            if isinstance(rich_component, ChartComponent):
                chart = dict(rich_component.data)
                chart_type = chart_type_from_figure(chart)

            if isinstance(rich_component, NotificationComponent):
                if getattr(rich_component, "level", "") == "error":
                    tool_error = getattr(rich_component, "message", "") or tool_error

            if isinstance(rich_component, RichTextComponent) and rich_component.content.strip():
                message = rich_component.content.strip()
            elif simple_component and getattr(simple_component, "text", "").strip():
                message = str(simple_component.text).strip()

        if not sql_query and message:
            sql_query = extract_sql_from_text(message)

        if not sql_query:
            # Direct LLM call: Gemini with a SQL-only prompt and the full schema.
            # This handles the case where the agent responds in prose instead of
            # calling run_sql — bypasses Vanna's tool-calling machinery entirely.
            if not schema_overview:
                schema_overview = get_schema_overview()
            sql_query = generate_sql_directly(question, schema_overview)
            if sql_query:
                log_event("direct_sql_generation", question=question)
            else:
                # Last resort: memory search, but only for genuinely close matches
                # (threshold 0.70 = same bar as the primary agent retrieval).
                sql_query, similarity = await memory_fallback_sql(question, request_context)
                if sql_query:
                    log_event("memory_fallback", similarity=similarity)
                else:
                    last_error = "The agent did not produce an executable SQL query."
                    continue

        if tool_error:
            last_error = tool_error
            continue

        if not rows and sql_query:
            try:
                validate_select_sql(sql_query)
                columns, rows = execute_select_sql(sql_query, DATABASE_PATH)
            except Exception as exc:
                last_error = str(exc)
                continue

        if rows:
            if not message or message.lower().startswith("error") or "unexpected error" in message.lower():
                message = "Query executed successfully."
        elif not message:
            message = "Query executed successfully."

        try:
            memory_context = await build_memory_context(request_context)
            await app_state.runtime.agent.agent_memory.save_tool_usage(
                question=question,
                tool_name="run_sql",
                args={"sql": sql_query},
                context=memory_context,
                success=True,
                metadata={"source": "auto_save"},
            )
        except Exception:
            pass

        return ChatResponse(
            message=message if rows else "No data found for that question.",
            sql_query=sql_query,
            columns=columns,
            rows=rows,
            row_count=len(rows),
            chart=chart,
            chart_type=chart_type if chart else "none",
        )

    raise ValueError(last_error or "The agent did not produce an executable SQL query.")


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
