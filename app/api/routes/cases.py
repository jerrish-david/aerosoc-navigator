from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps.services import get_approval_service, get_triage_service
from app.api.schemas.cases import (
    ApprovalRequest,
    ApprovalResponse,
    CaseDetailResponse,
    CaseTriageResponse,
)
from app.services.approval_service import ApprovalService
from app.services.triage_service import TriageService


router = APIRouter()


@router.get("/{case_id}", response_model=CaseDetailResponse)
def get_case(
    case_id: UUID,
    triage_service: TriageService = Depends(get_triage_service),
) -> CaseDetailResponse:
    return triage_service.get_case_detail(case_id)


@router.post("/{case_id}/triage", response_model=CaseTriageResponse)
def triage_case(
    case_id: UUID,
    triage_service: TriageService = Depends(get_triage_service),
) -> CaseTriageResponse:
    return triage_service.generate_triage(case_id)


@router.post("/{case_id}/approve", response_model=ApprovalResponse)
def approve_case_action(
    case_id: UUID,
    payload: ApprovalRequest,
    approval_service: ApprovalService = Depends(get_approval_service),
) -> ApprovalResponse:
    return approval_service.approve(case_id=case_id, payload=payload)

