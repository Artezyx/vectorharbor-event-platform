from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

class EventIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tenant_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{2,80}$")
    event_type: str = Field(pattern=r"^[a-z][a-z0-9_.-]{2,99}$")
    metadata: dict[str, Any] = Field(default_factory=dict)

class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: str
    event_type: str
    status: str
    created_at: datetime
    processed_at: datetime | None

class Page(BaseModel):
    items: list[EventOut]
    total: int
    page: int
    page_size: int
