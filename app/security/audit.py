import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime

from app.core.config import get_settings


@dataclass(slots=True)
class AuditEvent:
    actor: str
    action: str
    target_type: str
    target_id: str
    correlation_id: str
    created_at: datetime
    event_hash: str


class AuditService:
    def record(self, actor: str, action: str, target_type: str, target_id: str, correlation_id: str) -> AuditEvent:
        settings = get_settings()
        payload = {
            "seed": settings.audit_chain_seed,
            "actor": actor,
            "action": action,
            "target_type": target_type,
            "target_id": target_id,
            "correlation_id": correlation_id,
        }
        event_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
        return AuditEvent(
            actor=actor,
            action=action,
            target_type=target_type,
            target_id=target_id,
            correlation_id=correlation_id,
            created_at=datetime.now(UTC),
            event_hash=event_hash,
        )

