"""Event intake API demonstrating tenant isolation and idempotency."""
from datetime import datetime, timezone
from hashlib import sha256
from threading import RLock
from uuid import uuid4
import json

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="VectorHarbor Event Platform", version="0.1.0")


class EventInput(BaseModel):
    event_type: str = Field(min_length=1, max_length=100)
    payload: dict


class EventRecord(BaseModel):
    id: str
    tenant: str
    event_type: str
    payload: dict
    created_at: datetime
    replayed: bool = False


# In-memory store for the portfolio demo. Replace with PostgreSQL and
# a unique constraint (tenant, idempotency_key) in production.
_lock = RLock()
_events: dict[str, EventRecord] = {}
_idempotency: dict[tuple[str, str], tuple[str, str]] = {}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/events", response_model=EventRecord, status_code=201)
def ingest(
    event: EventInput,
    x_tenant_id: str = Header(min_length=1),
    idempotency_key: str = Header(min_length=1, max_length=128),
):
    canonical = event.model_dump_json()
    digest = sha256(canonical.encode("utf-8")).hexdigest()
    with _lock:
        identity = (x_tenant_id, idempotency_key)
        previous = _idempotency.get(identity)
        if previous is not None:
            event_id, old_digest = previous
            if old_digest != digest:
                raise HTTPException(status_code=409, detail="Idempotency key payload conflict")
            return _events[event_id].model_copy(update={"replayed": True})
        record = EventRecord(
            id=str(uuid4()), tenant=x_tenant_id, event_type=event.event_type,
            payload=event.payload, created_at=datetime.now(timezone.utc),
        )
        _events[record.id] = record
        _idempotency[identity] = (record.id, digest)
        return record


@app.get("/events/{event_id}", response_model=EventRecord)
def get_event(event_id: str, x_tenant_id: str = Header(min_length=1)):
    with _lock:
        event = _events.get(event_id)
        if event is None or event.tenant != x_tenant_id:
            raise HTTPException(status_code=404, detail="Event not found")
        return event
