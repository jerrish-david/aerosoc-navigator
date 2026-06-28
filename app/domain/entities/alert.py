from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(slots=True)
class Alert:
    id: UUID
    source: str
    external_id: str
    severity: str
    detected_at: datetime
    raw_payload: dict[str, object]
    asset_id: UUID | None = None

