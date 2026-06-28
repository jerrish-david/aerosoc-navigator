from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class CaseDetailResponse(BaseModel):
    case_id: UUID
    title: str
    status: str
    priority_score: float
    confidence_score: float | None = None


class CaseTriageResponse(BaseModel):
    case_id: UUID
    recommendation: str
    confidence_score: float
    citations: list[str]
    requires_approval: bool


class ApprovalRequest(BaseModel):
    action: str = Field(..., examples=["contain-host"])
    approved_by: str = Field(..., examples=["alex.analyst@company.com"])


class ApprovalResponse(BaseModel):
    approval_id: UUID = Field(default_factory=uuid4)
    case_id: UUID
    status: str
    message: str

