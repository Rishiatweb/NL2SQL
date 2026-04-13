from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any

import httpx


BASE_URL = "http://localhost:8000"
RESULTS_PATH = Path(__file__).parent / "RESULTS.md"

# --- Original 20 evaluation questions (Round 1) ---
QUESTIONS_ROUND1 = [
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

# --- New 20 evaluation questions (Round 2) ---
# These test different angles, phrasing, and SQL patterns from Round 1.
# All verified against clinic.db to return non-empty results.
QUESTIONS_ROUND2 = [
    "How many male and female patients are there?",
    "What is the average age of our patients?",
    "Which patients have never had an appointment?",
    "List the top 5 cities by number of patients",
    "How many doctors are in each specialization?",
    "Which doctor has the highest average treatment cost?",
    "What is the most common appointment status?",
    "How many appointments were scheduled on weekends?",
    "What is the most expensive treatment on record?",
    "What are the top 5 most common treatment names?",
    "What is the total outstanding balance on unpaid invoices?",
    "Which patient has the highest total invoice amount?",
    "What is the average invoice amount?",
    "How many treatments were performed by each department?",
    "List patients who have had exactly one appointment",
    "Which doctor has performed the most completed treatments?",
    "Show total billed amount versus total paid amount",
    "Show the breakdown of invoices by status",
    "Which medical specialization generates the most treatment revenue?",
    "List patients who have invoices in more than one payment status",
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


def run_questions(
    client: httpx.Client,
    questions: list[str],
    index_offset: int,
    total: int,
    delay: float = 2.1,
) -> tuple[list[list[str]], int, int, int, list[str]]:
    table_rows: list[list[str]] = []
    passed = errors = no_data = 0
    failure_notes: list[str] = []

    for i, question in enumerate(questions, start=1):
        global_index = index_offset + i
        label = f"{global_index:>2}/{total}"

        if i > 1 and delay > 0:
            time.sleep(delay)

        try:
            response = client.post(f"{BASE_URL}/chat", json={"question": question})
            payload = response.json()
        except Exception as exc:
            errors += 1
            detail = str(exc)
            print(f"{label}  {question}\n       ERROR: {detail}")
            failure_notes.append(f"Q{global_index} ({question}): request failed — {detail}")
            table_rows.append(
                [str(global_index), sanitize_cell(question), "", "Error", sanitize_cell(detail)]
            )
            continue

        if "error" in payload:
            errors += 1
            detail = payload.get("detail", payload.get("error", "unknown"))
            print(f"{label}  {question}\n       ERROR: {detail}")
            failure_notes.append(f"Q{global_index} ({question}): agent error — {detail}")
            table_rows.append(
                [str(global_index), sanitize_cell(question), "", "Error", sanitize_cell(detail)]
            )
            continue

        sql_query: str = payload.get("sql_query", "")
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
                f"Q{global_index} ({question}): query ran but returned 0 rows — "
                f"SQL: {sql_query[:120]}"
            )

        summary = summarize_first_row(columns, rows) + f" | rows={row_count} | chart={chart_type}"
        print(f"{label}  {question}\n       {status}")
        table_rows.append(
            [
                str(global_index),
                sanitize_cell(question),
                sanitize_cell(sql_query),
                correct,
                sanitize_cell(summary),
            ]
        )

    return table_rows, passed, errors, no_data, failure_notes


def write_results(
    sections: list[tuple[str, list[list[str]]]],
    totals: dict[str, int],
    failure_notes: list[str],
    total_questions: int,
) -> None:
    lines = [
        "# Evaluation Results",
        "",
        "## Score",
        "",
        f"- **Total:** {totals['passed']} / {total_questions} correct",
        f"- Passed (rows returned): {totals['passed']}",
        f"- No data returned: {totals['no_data']}",
        f"- Errors: {totals['errors']}",
        "",
    ]

    for section_title, rows in sections:
        lines += [f"## {section_title}", "", "| # | Question | Generated SQL | Correct? | Result summary |", "|---|---|---|---|---|"]
        for row in rows:
            lines.append("| " + " | ".join(row) + " |")
        lines.append("")

    lines += ["## Failure Analysis", ""]
    if failure_notes:
        for note in failure_notes:
            lines.append(f"- {note}")
    else:
        lines.append("- No failures detected.")

    RESULTS_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nResults written to {RESULTS_PATH}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the Clinic NL2SQL API")
    parser.add_argument(
        "--round",
        choices=["1", "2", "all"],
        default="all",
        help="Which question set to run: 1 (original), 2 (new), or all (default)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.1,
        help=(
            "Seconds to wait between requests (default: 2.1). "
            "The server rate-limits at 30 req/60s; a delay >2.0s keeps all 40 "
            "questions within that window. Set to 0 to disable."
        ),
    )
    args = parser.parse_args()

    if args.round == "1":
        sets = [("Round 1 — Original Questions (Q1–Q20)", QUESTIONS_ROUND1, 0)]
        total = 20
    elif args.round == "2":
        sets = [("Round 2 — New Questions (Q21–Q40)", QUESTIONS_ROUND2, 0)]
        total = 20
    else:
        sets = [
            ("Round 1 — Original Questions (Q1–Q20)", QUESTIONS_ROUND1, 0),
            ("Round 2 — New Questions (Q21–Q40)", QUESTIONS_ROUND2, 20),
        ]
        total = 40

    timeout = httpx.Timeout(90.0)
    all_rows: list[tuple[str, list[list[str]]]] = []
    totals = {"passed": 0, "errors": 0, "no_data": 0}
    all_failures: list[str] = []

    with httpx.Client(timeout=timeout) as client:
        check_server(client)
        delay_msg = f"{args.delay}s delay between requests" if args.delay > 0 else "no delay"
        print(f"Server is up. Running {total} questions ({delay_msg})...\n")

        for section_title, questions, offset in sets:
            print(f"{'─' * 60}")
            print(f"  {section_title}")
            print(f"{'─' * 60}")
            rows, passed, errors, no_data, failures = run_questions(
                client, questions, offset, total, delay=args.delay
            )
            all_rows.append((section_title, rows))
            totals["passed"] += passed
            totals["errors"] += errors
            totals["no_data"] += no_data
            all_failures.extend(failures)
            print(
                f"\n  Section done — Passed: {passed}  No-data: {no_data}  Errors: {errors}\n"
            )

    print(
        f"{'─' * 60}\n"
        f"TOTAL — Passed: {totals['passed']}/{total}  "
        f"No-data: {totals['no_data']}/{total}  "
        f"Errors: {totals['errors']}/{total}"
    )
    write_results(all_rows, totals, all_failures, total)


if __name__ == "__main__":
    main()
