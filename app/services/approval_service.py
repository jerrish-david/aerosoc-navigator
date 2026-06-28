from uuid import UUID

from app.api.schemas.cases import ApprovalRequest, ApprovalResponse
from app.security.audit import AuditService


class ApprovalService:
    def __init__(self, audit_service: AuditService) -> None:
        self._audit_service = audit_service

    def approve(self, case_id: UUID, payload: ApprovalRequest) -> ApprovalResponse:
        # Pseudocode:
        # 1. Validate that the approver has the correct role.
        # 2. Confirm the requested action is pending approval for this case.
        # 3. Record the approval in the approvals table.
        # 4. Emit an immutable audit event and notify downstream workflow handlers.
        self._audit_service.record(
            actor=payload.approved_by,
            action=f"approved:{payload.action}",
            target_type="case",
            target_id=str(case_id),
            correlation_id=str(case_id),
        )
        return ApprovalResponse(
            case_id=case_id,
            status="approved",
            message=f"Action '{payload.action}' approved and audit event recorded.",
        )

