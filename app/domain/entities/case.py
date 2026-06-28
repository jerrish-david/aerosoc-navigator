from dataclasses import dataclass
from uuid import UUID


@dataclass(slots=True)
class Case:
    id: UUID
    title: str
    status: str
    priority_score: float
    confidence_score: float | None = None

