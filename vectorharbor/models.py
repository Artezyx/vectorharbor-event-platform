import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, Index, JSON, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base

class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_tenant_key"),
        Index("ix_tenant_status_created", "tenant_id", "status", "created_at"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(80), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    metadata_payload: Mapped[dict] = mapped_column("payload", JSON, nullable=False)
    request_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
