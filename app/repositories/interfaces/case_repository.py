from typing import Protocol
from uuid import UUID

from app.domain.entities.case import Case


class CaseRepository(Protocol):
    def save(self, case: Case) -> Case:
        ...

    def get(self, case_id: UUID) -> Case | None:
        ...

