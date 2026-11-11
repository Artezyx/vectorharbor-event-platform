from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from .database import Base, engine, get_db
from .models import Event
from .schema import EventIn, EventOut, Page
from .security import Principal, require_principal, require_scope
from .service import ConflictError, store
from .tasks import process_event

app = FastAPI(title="VectorHarbor API", version="1.1.0")

@app.on_event("startup")
def create_dev_schema():
    # Local demo only; use Alembic migration in deployed environments.
    Base.metadata.create_all(bind=engine)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/v1/events", response_model=EventOut, status_code=status.HTTP_202_ACCEPTED)
def ingest(
    payload: EventIn, db: Session = Depends(get_db),
    idempotency_key: str = Header(min_length=1, max_length=128),
    principal: Principal = Depends(require_principal),
):
    require_scope(principal, payload.tenant_id, "events:write")
    try:
        event, replay = store(db, payload, idempotency_key)
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not replay:
        process_event.delay(str(event.id))
    return event

@app.get("/v1/events", response_model=Page)
def history(
    tenant_id: str = Query(min_length=2, max_length=80), page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db), principal: Principal = Depends(require_principal),
):
    require_scope(principal, tenant_id, "events:read")
    base = select(Event).where(Event.tenant_id == principal.tenant_id)
    items = db.scalars(base.order_by(Event.created_at.desc(), Event.id.desc())
                       .offset((page - 1) * page_size).limit(page_size)).all()
    total = db.scalar(select(func.count(Event.id)).where(Event.tenant_id == principal.tenant_id)) or 0
    return Page(items=[EventOut.model_validate(e) for e in items], total=total,
                page=page, page_size=page_size)

@app.get("/v1/metrics")
def metrics(
    tenant_id: str = Query(min_length=2, max_length=80),
    db: Session = Depends(get_db), principal: Principal = Depends(require_principal),
):
    require_scope(principal, tenant_id, "events:read")
    rows = db.execute(select(Event.event_type, func.count(Event.id)).where(
        Event.tenant_id == principal.tenant_id, Event.status == "processed"
    ).group_by(Event.event_type)).all()
    return {"tenant_id": principal.tenant_id, "processed_by_type": dict(rows)}
