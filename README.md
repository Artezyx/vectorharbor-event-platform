# VectorHarbor — Event Processing Platform

Python / FastAPI backend portfolio project for remote backend engineering roles.

## Current implementation
- REST event ingestion and retrieval
- Tenant-scoped access
- Idempotency-key replay and conflict detection
- Automated tests in GitHub Actions

## Run
```bash
python -m pip install -e '.[test]'
uvicorn vectorharbor.main:app --reload
python -m pytest -q
```
Open API docs: http://localhost:8000/docs

**Architecture note:** The committed demo uses an in-memory store for a self-contained review. PostgreSQL, Redis and Celery are planned extensions and are **not yet implemented** in this published version.
