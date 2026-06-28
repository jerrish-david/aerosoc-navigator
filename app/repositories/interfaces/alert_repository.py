from typing import Protocol
from uuid import UUID

from app.domain.entities.alert import Alert


class AlertRepository(Protocol):
    def save(self, alert: Alert) -> Alert:
        ...

    def get(self, alert_id: UUID) -> Alert | None:
        ...

