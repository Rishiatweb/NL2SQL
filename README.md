# Clinic NL2SQL Backend

A production-oriented Natural Language to SQL backend built with FastAPI, SQLite, Plotly, and Vanna AI 2.0. Accepts a natural language question, generates SQL via a Vanna agent backed by Gemini `gemini-2.5-flash`, validates the SQL for safety, runs it against a clinic database, and returns structured results with optional charts.

## Architecture

- `setup_database.py` — creates `clinic.db` and seeds realistic clinic data (patients, doctors, appointments, treatments, invoices).
- `seed_memory.py` — validates and persists 42 canonical NL→SQL examples into `agent_memory_seed.json`.
- `vanna_setup.py` — builds the Vanna 2.0 agent with `GeminiLlmService`, `SqliteRunner`, `DemoAgentMemory`, `DefaultLlmContextEnhancer`, and the required tools.
- `main.py` — FastAPI application exposing `/chat` and `/health` with rate limiting, response caching, and a multi-layer SQL generation fallback.
- `project_utils.py` — SQL validation, seed loading, logging helpers, and chart type detection.
- `evaluate.py` — automated evaluation script for the 40-question test set.

`DemoAgentMemory` is in-memory only; `agent_memory_seed.json` is the bootstrap source loaded at startup.

## How questions are answered

Every incoming question goes through a layered resolution chain:

1. **Seed retrieval (similarity ≥ 0.70)** — `DemoAgentMemory` searches the 42 seed examples using Jaccard + SequenceMatcher similarity. A close match returns verified SQL directly, no LLM call needed.
2. **Vanna agent with schema context** — for questions below the threshold, the agent receives the full table/column schema via `DefaultLlmContextEnhancer` and generates SQL by calling the `run_sql` tool.
3. **Text extraction** — if the agent replies in prose with an embedded SELECT block, the SQL is extracted via regex.
4. **Direct Gemini call** — if the agent pipeline stalls entirely, `generate_sql_directly()` calls Gemini with a tight SQL-only prompt (schema + enum values, no markdown). This handles any novel question without a seed.
5. **Memory fallback (threshold 0.70)** — last resort; only fires when a genuinely close seed exists.

Successfully executed SQL is saved back into `DemoAgentMemory`, so the agent learns from every answered question.

## Requirements

- Python 3.10+
- Google Gemini API key

Create a `.env` file in the project root:

```env
GOOGLE_API_KEY=your_google_ai_studio_key
```

## Setup

```bash
pip install -r requirements.txt
python setup_database.py
python seed_memory.py
uvicorn main:app --port 8000
```

## Running the Evaluation

With the server running, execute all 40 test questions and write `RESULTS.md`:

```bash
python evaluate.py             # all 40 questions (default)
python evaluate.py --round 1   # original 20 only
python evaluate.py --round 2   # extended 20 only
python evaluate.py --delay 0   # no delay (safe for ≤ 30 questions)
```

The server rate-limits at 30 requests per 60 seconds. The default 2.1 s inter-request delay keeps all 40 questions within that window.

## API

### `GET /health`

```json
{
  "status": "ok",
  "database": "connected",
  "agent_memory_items": 42
}
```

### `POST /chat`

Request:

```json
{
  "question": "Show revenue by doctor"
}
```

Response:

```json
{
  "message": "Here is the revenue by doctor.",
  "sql_query": "SELECT d.name, ROUND(SUM(t.cost), 2) AS total_revenue ...",
  "columns": ["name", "total_revenue"],
  "rows": [["Dr. Elena Foster", 119872.01]],
  "row_count": 15,
  "chart": { "data": [], "layout": {} },
  "chart_type": "bar"
}
```

Error responses use HTTP 400 / 422 / 429 / 500 with a consistent shape:

```json
{
  "error": "Rate limit exceeded",
  "detail": "Too many requests. Please wait a moment and try again.",
  "code": "rate_limit_exceeded"
}
```

## Safety

- Only `SELECT` and `WITH ... SELECT` (CTE) queries are allowed.
- `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, and other write keywords are blocked.
- `sqlite_%` system table access is rejected.
- SQL comments (`--`, `/* */`) are rejected.
- Multiple statements in one query are rejected.
- Empty and overly long questions are rejected before reaching the agent.
- Rate limited at 30 requests per 60-second sliding window per client IP.
- Responses are cached in-memory by normalized question text.

## LLM

```python
from vanna.integrations.google import GeminiLlmService
llm_service = GeminiLlmService(model="gemini-2.5-flash", api_key=api_key)
```

The same model (`gemini-2.5-flash`) is used for both the Vanna agent pipeline and the direct SQL generation fallback.
