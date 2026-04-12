from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import httpx


BASE_URL = "http://localhost:8000"
RESULTS_PATH = Path(__file__).parent / "RESULTS.md"

QUESTIONS = [
    "How many patients do we have?",
    "List all doctors and their specializations",
    "Show me appointments for last month",
    "Which doctor has the most appointments?",
    "What is the total revenue?",
    "Show revenue by doctor",
    "How many cancelled appointments last quarter?",
    "Top 5 patients by spending",
    "Average treatment cost by specialization",
    "Show monthly appointment count for the past 6 months",
    "Which city has the most patients?",
    "List patients who visited more than 3 times",
    "Show unpaid invoices",
    "What percentage of appointments are no-shows?",
    "Show the busiest day of the week for appointments",
    "Revenue trend by month",
    "Average appointment duration by doctor",
    "List patients with overdue invoices",
    "Compare revenue between departments",
    "Show patient registration trend by month",
]


def sanitize_cell(value: Any) -> str:
    return str(value).replace("\n", " ").replace("|", "\\|")


def summarize_first_row(columns: list[str], rows: list[list[Any]]) -> str:
    if not rows or not columns:
        return "—"
    pairs = ", ".join(f"{c}={v}" for c, v in zip(columns, rows[0]))
    return pairs[:120] + ("…" if len(pairs) > 120 else "")


def check_server(client: httpx.Client) -> None:
    try:
        resp = client.get(f"{BASE_URL}/health", timeout=10.0)
        resp.raise_for_status()
    except Exception as exc:
        print(
            f"Server not reachable at {BASE_URL}. "
            "Start it with: uvicorn main:app --port 8000\n"
            f"Detail: {exc}"
        )
        sys.exit(1)


def write_results(
    table_rows: list[list[str]],
    passed: int,
    errors: int,
    no_data: int,
    failure_notes: list[str],
) -> None:
    lines = [
        "# Evaluation Results",
        "",
        "## Score",
        "",
        f"- **Total:** {passed} / 20 correct",
        f"- Passed (rows returned): {passed}",
        f"- No data returned: {no_data}",
        f"- Errors: {errors}",
        "",
        "## Questions",
        "",
        "| # | Question | Generated SQL | Correct? | Result summary |",
        "|---|---|---|---|---|",
    ]
    for row in table_rows:
        lines.append("| " + " | ".join(row) + " |")

    lines.append("")
    lines.append("## Failure Analysis")
    lines.append("")
    if failure_notes:
        for note in failure_notes:
            lines.append(f"- {note}")
    else:
        lines.append("- No failures detected.")

    RESULTS_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nResults written to {RESULTS_PATH}")


def main() -> None:
    timeout = httpx.Timeout(90.0)
    table_rows: list[list[str]] = []
    passed = 0
    errors = 0
    no_data = 0
    failure_notes: list[str] = []

    with httpx.Client(timeout=timeout) as client:
        check_server(client)
        print(f"Server is up. Running {len(QUESTIONS)} questions...\n")

        for index, question in enumerate(QUESTIONS, start=1):
            try:
                response = client.post(
                    f"{BASE_URL}/chat", json={"question": question}
                )
                payload = response.json()
            except Exception as exc:
                errors += 1
                label = f"Q{index}"
                detail = str(exc)
                print(f"{index:>2}/20  {question}\n       ERROR: {detail}")
                failure_notes.append(f"Q{index} ({question}): request failed — {detail}")
                table_rows.append(
                    [str(index), sanitize_cell(question), "", "Error", sanitize_cell(detail)]
                )
                continue

            if "error" in payload:
                errors += 1
                detail = payload.get("detail", payload.get("error", "unknown"))
                print(f"{index:>2}/20  {question}\n       ERROR: {detail}")
                failure_notes.append(
                    f"Q{index} ({question}): agent error — {detail}"
                )
                table_rows.append(
                    [str(index), sanitize_cell(question), "", "Error", sanitize_cell(detail)]
                )
                continue

            sql_query = payload.get("sql_query", "")
            columns: list[str] = payload.get("columns") or []
            rows: list[list[Any]] = payload.get("rows") or []
            row_count: int = payload.get("row_count", len(rows))
            chart_type: str = payload.get("chart_type", "none")

            if row_count > 0:
                passed += 1
                correct = "Yes"
                status = f"OK ({row_count} rows, chart={chart_type})"
            else:
                no_data += 1
                correct = "Check"
                status = "No data returned"
                failure_notes.append(
                    f"Q{index} ({question}): query ran but returned 0 rows — "
                    f"SQL: {sql_query[:120]}"
                )

            summary = summarize_first_row(columns, rows) + f" | rows={row_count} | chart={chart_type}"
            print(f"{index:>2}/20  {question}\n       {status}")
            table_rows.append(
                [
                    str(index),
                    sanitize_cell(question),
                    sanitize_cell(sql_query),
                    correct,
                    sanitize_cell(summary),
                ]
            )

    print(f"\nDone. Passed: {passed}/20  No-data: {no_data}/20  Errors: {errors}/20")
    write_results(table_rows, passed, errors, no_data, failure_notes)


if __name__ == "__main__":
    main()
