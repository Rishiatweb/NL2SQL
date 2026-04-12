from __future__ import annotations

import sys
from typing import Any

import httpx


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
    text = str(value)
    text = text.replace("\n", " ").replace("|", "\\|")
    return text


def summarize_first_row(rows: list[list[Any]]) -> str:
    if not rows:
        return "first_row=None"
    return f"first_row={rows[0]}"


def write_results(table_rows: list[list[str]], passed: int, errors: int, no_data: int) -> None:
    lines = [
        "# Evaluation Results",
        "",
        "| # | Question | Generated SQL | Correct? | Result summary |",
        "|---|---|---|---|---|",
    ]
    for row in table_rows:
        lines.append("| " + " | ".join(row) + " |")
    lines.extend(
        [
            "",
            "## Score",
            f"Passed (rows returned): {passed} / 20",
            f"Errors: {errors} / 20",
            f"No data: {no_data} / 20",
        ]
    )
    with open("RESULTS.md", "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def main() -> None:
    url = "http://localhost:8000/chat"
    timeout = httpx.Timeout(60.0)
    table_rows: list[list[str]] = []
    passed = 0
    errors = 0
    no_data = 0

    try:
        with httpx.Client(timeout=timeout) as client:
            for index, question in enumerate(QUESTIONS, start=1):
                try:
                    response = client.post(url, json={"question": question})
                except httpx.RequestError as exc:
                    print(f"{index}/20 {question} ERROR (request failed: {exc})")
                    errors += 1
                    table_rows.append(
                        [
                            str(index),
                            sanitize_cell(question),
                            sanitize_cell(f"Error: {exc}"),
                            "Error",
                            sanitize_cell(f"error={exc}"),
                        ]
                    )
                    continue

                payload = response.json()
                if "error" in payload:
                    errors += 1
                    detail = payload.get("detail", payload.get("error"))
                    print(f"{index}/20 {question} ERROR ({detail})")
                    table_rows.append(
                        [
                            str(index),
                            sanitize_cell(question),
                            sanitize_cell(""),
                            "Error",
                            sanitize_cell(f"error={detail}"),
                        ]
                    )
                    continue

                sql_query = payload.get("sql_query", "")
                rows = payload.get("rows") or []
                row_count = payload.get("row_count", len(rows))
                chart_type = payload.get("chart_type", "none")

                if row_count and row_count > 0:
                    passed += 1
                    correct = "Yes"
                    status = f"OK ({row_count} rows)"
                else:
                    no_data += 1
                    correct = "Check"
                    status = "No data"

                summary = f"{summarize_first_row(rows)} | rows={row_count} | chart={chart_type}"

                print(f"{index}/20 {question} {status}")
                table_rows.append(
                    [
                        str(index),
                        sanitize_cell(question),
                        sanitize_cell(sql_query),
                        correct,
                        sanitize_cell(summary),
                    ]
                )
    except httpx.RequestError as exc:
        print("Server is not reachable. Start the API with uvicorn before running evaluate.py.")
        sys.exit(1)

    write_results(table_rows, passed, errors, no_data)


if __name__ == "__main__":
    main()
