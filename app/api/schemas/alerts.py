from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class AlertCreateRequest(BaseModel):
    source: str = Field(..., examples=["mock-siem"])
    external_id: str = Field(..., examples=["alert-123"])
    asset_id: UUID | None = None
    severity: str = Field(..., examples=["high"])
    detected_at: datetime
    raw_payload: dict[str, object]


class AlertCreateResponse(BaseModel):
    alert_id: UUID = Field(default_factory=uuid4)
    case_id: UUID = Field(default_factory=uuid4)
    status: str
    message: str

