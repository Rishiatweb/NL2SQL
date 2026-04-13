from __future__ import annotations

import json
import logging
import re
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "clinic.db"
SEED_FILE_PATH = BASE_DIR / "agent_memory_seed.json"
MAX_QUESTION_LENGTH = 500

LOGGER = logging.getLogger("nl2sql")


class SqlValidationError(ValueError):
    """Raised when SQL does not meet the project's safety rules."""


@dataclass(slots=True)
class SeedExample:
    question: str
    sql: str
    category: str


BLOCKED_KEYWORDS = {
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "EXEC",
    "EXECUTE",
    "GRANT",
    "REVOKE",
    "ATTACH",
    "DETACH",
    "PRAGMA",
    "CREATE",
    "REPLACE",
    "TRUNCATE",
    "VACUUM",
}

COMMENT_PATTERNS = (
    re.compile(r"--"),
    re.compile(r"/\*"),
)

SQLITE_SYSTEM_PATTERN = re.compile(r"\bsqlite_[a-z0-9_]+\b", re.IGNORECASE)


def configure_logging() -> None:
    if logging.getLogger().handlers:
        return

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def log_event(event: str, **payload: Any) -> None:
    LOGGER.info(json.dumps({"event": event, **payload}, default=str))


def normalize_question(question: str) -> str:
    return " ".join(question.lower().split())


def validate_question(question: str) -> str:
    cleaned = question.strip()
    if not cleaned:
        raise ValueError("Question must not be empty.")
    if len(cleaned) > MAX_QUESTION_LENGTH:
        raise ValueError(
            f"Question is too long. Maximum length is {MAX_QUESTION_LENGTH} characters."
        )
    return cleaned


def _strip_trailing_semicolon(sql: str) -> str:
    stripped = sql.strip()
    return stripped[:-1].rstrip() if stripped.endswith(";") else stripped


def validate_select_sql(sql: str) -> None:
    if not sql or not sql.strip():
        raise SqlValidationError("SQL query is empty.")

    stripped = sql.strip()

    for pattern in COMMENT_PATTERNS:
        if pattern.search(stripped):
            raise SqlValidationError("SQL comments are not allowed.")

    if stripped.count(";") > 1 or ";" in stripped[:-1]:
        raise SqlValidationError("Multiple SQL statements are not allowed.")

    candidate = _strip_trailing_semicolon(stripped)
    upper_candidate = candidate.upper()

    if not upper_candidate.startswith("SELECT") and not upper_candidate.startswith("WITH"):
        raise SqlValidationError("Only SELECT statements are allowed.")

    # WITH queries must contain SELECT and must not be data-modifying CTEs
    if upper_candidate.startswith("WITH") and "SELECT" not in upper_candidate:
        raise SqlValidationError("WITH clauses must contain a SELECT statement.")

    tokens = set(re.findall(r"\b[A-Z_]+\b", upper_candidate))
    blocked = sorted(tokens & BLOCKED_KEYWORDS)
    if blocked:
        raise SqlValidationError(
            f"Blocked SQL keyword detected: {', '.join(blocked)}."
        )

    system_match = SQLITE_SYSTEM_PATTERN.search(candidate)
    if system_match:
        raise SqlValidationError(
            f"Access to system tables is not allowed: {system_match.group(0)}."
        )


def execute_select_sql(
    sql: str, database_path: Path = DATABASE_PATH
) -> tuple[list[str], list[list[Any]]]:
    validate_select_sql(sql)

    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row

    try:
        cursor = connection.execute(_strip_trailing_semicolon(sql))
        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description or []]
        result_rows = [[row[column] for column in columns] for row in rows]
        return columns, result_rows
    finally:
        connection.close()


def save_seed_pairs(
    seed_examples: list[SeedExample], seed_file_path: Path = SEED_FILE_PATH
) -> None:
    payload = [asdict(example) for example in seed_examples]
    seed_file_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_seed_pairs(seed_file_path: Path = SEED_FILE_PATH) -> list[SeedExample]:
    if not seed_file_path.exists():
        return []

    raw_items = json.loads(seed_file_path.read_text(encoding="utf-8"))
    return [SeedExample(**item) for item in raw_items]


def chart_type_from_figure(chart_payload: dict[str, Any]) -> str:
    traces = chart_payload.get("data", [])
    if not traces:
        return "none"

    first_trace_type = str(traces[0].get("type", "")).lower()
    if first_trace_type == "bar":
        return "bar"
    if first_trace_type in {"scatter", "scattergl", "line"}:
        return "line"
    if first_trace_type == "pie":
        return "pie"
    return "other"
