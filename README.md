# Clinic NL2SQL Backend

This project is a production-oriented Natural Language to SQL backend built with FastAPI, SQLite, Plotly, and Vanna AI 2.0. It accepts a natural language question, uses a Vanna agent backed by Gemini `gemini-2.5-flash` to generate SQL, validates the SQL for safety, runs it against a clinic database, and returns structured results with summaries and optional charts.

## Architecture

- `setup_database.py` creates `clinic.db` and seeds realistic clinic data.
- `seed_memory.py` validates and persists 15 canonical NL→SQL examples into `agent_memory_seed.json`.
- `vanna_setup.py` builds the Vanna 2.0 agent with `GeminiLlmService`, `SqliteRunner`, `DemoAgentMemory`, and the required tools.
- `main.py` exposes custom FastAPI endpoints for `/chat` and `/health`.
- `project_utils.py` centralizes SQL validation, seed loading, logging, and helper logic.

`DemoAgentMemory` is in-memory only, so the project uses `agent_memory_seed.json` as a bootstrap source. Running `seed_memory.py` makes the required standalone seeding step useful across processes.

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

## API

### `GET /health`

```json
{
  "status": "ok",
  "database": "connected",
  "agent_memory_items": 15
}
```

### `POST /chat`

Request:

```json
{
  "question": "Show revenue by doctor"
}
```

Response shape:

```json
{
  "message": "Here is the revenue by doctor.",
  "sql_query": "SELECT ...",
  "columns": ["name", "total_revenue"],
  "rows": [["Dr. Amelia Allen", 12750.25]],
  "row_count": 1,
  "chart": {
    "data": [],
    "layout": {}
  },
  "chart_type": "bar"
}
```

## Safety and Robustness

- Only `SELECT` queries are allowed.
- Dangerous SQL keywords and `sqlite_%` system tables are rejected.
- Empty and overly long questions are rejected.
- Responses are cached in-memory by normalized question.
- Basic structured logging is included.
- `/chat` is rate limited with simple in-memory middleware.

## LLM Choice

This implementation uses Google Gemini via:

```python
from vanna.integrations.google import GeminiLlmService
```

Configured model:

- `gemini-2.5-flash`
