# VectorHarbor — Multi-Tenant Event Processing Platform
**Target role:** Remote Python backend engineer (FastAPI, Python 3.12+, PostgreSQL, SQLAlchemy 2, Redis, Celery, Docker, pytest).

Event ingestion for SaaS applications with tenant-aware idempotency, strongly validated payloads, asynchronous processing and operational metrics. A duplicate request returns the original event without counting it twice; a conflicting replay gets HTTP 409.

## System design
```text
Clients -> FastAPI -> PostgreSQL (transaction + unique tenant/key)
               |                  ^
               v                  |
          Redis queue -> Celery worker (row lock, state transition)
```

### Features
- Multi-tenant event ownership (`tenant_id`), event UUID, event type and JSON metadata.
- Deterministic SHA-256 request fingerprints (canonical JSON), unique `tenant_id + key` invariant.
- Concurrent-safe event processing: database row locking and durable status.
- Redis-backed Celery task queue; JSON-serializable task arguments.
- Filtered event history, paginated results, counts by event type.
- Strict request validation and automated tests for retries/conflicts.
- Docker Compose, Dockerfile, GitHub Actions and SQLAlchemy models.

## Quick start
```bash
cp .env.example .env
# replace demo credentials before using outside your machine
docker compose --env-file .env up --build
```
API: `http://localhost:8091` · OpenAPI: `/docs` · Redis and PostgreSQL are internal to Compose.

```bash
curl -X POST http://localhost:8091/v1/events \
 -H 'Content-Type: application/json' -H 'Idempotency-Key: tenant-event-0001' \
 -d '{"tenant_id":"acme","event_type":"invoice.paid","metadata":{"amount":400,"currency":"MXN"}}'
curl 'http://localhost:8091/v1/metrics?tenant_id=acme'
```

## Tests
```bash
python -m pip install -e '.[dev]'
pytest -q
```
Tests use isolated SQLite for transactional service invariants; CI also builds a Python environment. PostgreSQL-specific locking and worker integration should be verified using a Docker smoke test before deployment.

## Engineering notes
Task publication happens after the database commit (good for the demo; a broker outage can leave a queued-but-unpublished event). In production, add a transactional outbox and a publisher retry loop. API key/OIDC authentication and cross-tenant authorization are required before opening the API publicly. This project intentionally does not claim production completeness.
