import hashlib
import json
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .models import Event
from .schema import EventIn

class ConflictError(Exception):
    pass

def fingerprint(data: EventIn) -> str:
    # Stable across differences in JSON key order and whitespace.
    raw = json.dumps(data.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def store(db: Session, data: EventIn, key: str) -> tuple[Event, bool]:
    digest = fingerprint(data)
    current = db.scalar(select(Event).where(Event.tenant_id == data.tenant_id, Event.idempotency_key == key))
    if current:
        if current.request_digest != digest:
            raise ConflictError("Idempotency key was reused with a different request")
        return current, True
    event = Event(tenant_id=data.tenant_id, idempotency_key=key, event_type=data.event_type,
                  metadata_payload=data.metadata, request_digest=digest)
    try:
        db.add(event)
        db.commit()
        db.refresh(event)
        return event, False
    except IntegrityError:
        # A concurrent writer won the unique constraint. Read the committed winner.
        db.rollback()
        winner = db.scalar(select(Event).where(Event.tenant_id == data.tenant_id, Event.idempotency_key == key))
        if winner is None or winner.request_digest != digest:
            raise ConflictError("Conflicting concurrent event write")
        return winner, True

def process(db: Session, event_id: UUID) -> bool:
    event = db.scalar(select(Event).where(Event.id == event_id).with_for_update())
    if event is None or event.status == "processed":
        return False
    from datetime import datetime, timezone
    event.status = "processed"
    event.processed_at = datetime.now(timezone.utc)
    db.commit()
    return True
