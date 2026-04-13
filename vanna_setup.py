from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from vanna import Agent, AgentConfig
from vanna.capabilities.sql_runner import RunSqlToolArgs
from vanna.components import NotificationComponent, SimpleTextComponent, UiComponent
from vanna.core.registry import ToolRegistry
from vanna.core.tool import ToolContext, ToolResult
from vanna.core.user import RequestContext, User, UserResolver
from vanna.integrations.google import GeminiLlmService
from vanna.integrations.local.agent_memory import DemoAgentMemory
from vanna.integrations.sqlite import SqliteRunner
from vanna.tools import RunSqlTool, VisualizeDataTool
from vanna.tools.agent_memory import (
    SaveQuestionToolArgsTool,
    SearchSavedCorrectToolUsesTool,
)

from project_utils import (
    DATABASE_PATH,
    SEED_FILE_PATH,
    SeedExample,
    configure_logging,
    load_seed_pairs,
    log_event,
    validate_select_sql,
)


@dataclass(slots=True)
class VannaRuntime:
    agent: Agent
    seed_count: int


class DefaultUserResolver(UserResolver):
    async def resolve_user(self, request_context: RequestContext) -> User:
        return User(
            id="default-user",
            username="default-user",
            email="default@example.com",
            group_memberships=["admin", "user"],
            metadata={"remote_addr": request_context.remote_addr},
        )


class ValidatedRunSqlTool(RunSqlTool):
    async def execute(self, context: ToolContext, args: RunSqlToolArgs) -> ToolResult:
        try:
            validate_select_sql(args.sql)
        except Exception as exc:
            message = f"Query rejected by safety validation: {exc}"
            return ToolResult(
                success=False,
                result_for_llm=message,
                error=message,
                ui_component=UiComponent(
                    rich_component=NotificationComponent(level="error", message=message),
                    simple_component=SimpleTextComponent(text=message),
                ),
            )
        return await super().execute(context, args)


async def _seed_agent_memory(memory: DemoAgentMemory, examples: list[SeedExample]) -> int:
    seed_context = ToolContext(
        user=User(id="seed-loader", username="seed-loader", group_memberships=["admin"]),
        conversation_id="seed-memory",
        request_id="seed-memory",
        agent_memory=memory,
        metadata={"seed_file": str(SEED_FILE_PATH)},
    )

    for example in examples:
        await memory.save_tool_usage(
            question=example.question,
            tool_name="run_sql",
            args={"sql": example.sql},
            context=seed_context,
            success=True,
            metadata={"category": example.category, "source": "bootstrap_seed"},
        )

    return len(examples)


async def get_agent() -> VannaRuntime:
    configure_logging()
    load_dotenv()

    if not Path(DATABASE_PATH).exists():
        raise FileNotFoundError(
            "clinic.db was not found. Run `python setup_database.py` before starting the API."
        )

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError(
            "GOOGLE_API_KEY is required. Add it to your environment or .env file before starting the API."
        )

    llm_service = GeminiLlmService(model="gemini-2.5-flash", api_key=api_key)
    agent_memory = DemoAgentMemory(max_items=20_000)
    tool_registry = ToolRegistry()
    sqlite_runner = SqliteRunner(database_path=str(DATABASE_PATH))

    tool_registry.register_local_tool(ValidatedRunSqlTool(sql_runner=sqlite_runner), [])
    tool_registry.register_local_tool(VisualizeDataTool(), [])
    tool_registry.register_local_tool(SaveQuestionToolArgsTool(), [])
    tool_registry.register_local_tool(SearchSavedCorrectToolUsesTool(), [])

    seed_examples = load_seed_pairs()
    seed_count = await _seed_agent_memory(agent_memory, seed_examples)

    agent = Agent(
        llm_service=llm_service,
        tool_registry=tool_registry,
        user_resolver=DefaultUserResolver(),
        agent_memory=agent_memory,
        config=AgentConfig(stream_responses=True, max_tool_iterations=8),
    )

    log_event("agent_initialized", seed_count=seed_count)
    return VannaRuntime(agent=agent, seed_count=seed_count)
