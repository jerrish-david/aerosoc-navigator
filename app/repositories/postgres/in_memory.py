from uuid import UUID

from app.domain.entities.alert import Alert
from app.domain.entities.case import Case


class InMemoryAlertRepository:
    _storage: dict[UUID, Alert] = {}

    def save(self, alert: Alert) -> Alert:
        self._storage[alert.id] = alert
        return alert

    def get(self, alert_id: UUID) -> Alert | None:
        return self._storage.get(alert_id)


class InMemoryCaseRepository:
    _storage: dict[UUID, Case] = {}

    def save(self, case: Case) -> Case:
        self._storage[case.id] = case
        return case

    def get(self, case_id: UUID) -> Case | None:
        return self._storage.get(case_id)

