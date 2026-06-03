# RAG-KB Backend

FastAPI backend skeleton for the private RAG knowledge base.

## Commands

```powershell
uv sync
uv run uvicorn app.main:app --reload --port 8000
uv run pytest -v
uv run ruff check .
uv run ruff format --check .
uv run mypy app
```

## Layout

- `app/api/`: FastAPI routers
- `app/core/`: configuration, logging, exceptions, dependencies
- `app/services/`: service integrations added by later tasks
- `app/models/`: Pydantic schemas
- `app/workflows/`: LlamaIndex workflows added by later tasks
- `tests/`: pytest test suite
