from app.repositories.postgres.in_memory import InMemoryAlertRepository, InMemoryCaseRepository
from app.security.audit import AuditService
from app.security.output_guard import OutputGuard
from app.security.prompt_guard import PromptGuard
from app.services.approval_service import ApprovalService
from app.services.risk_engine import RiskEngine
from app.services.triage_service import TriageService


def get_triage_service() -> TriageService:
    return TriageService(
        alert_repository=InMemoryAlertRepository(),
        case_repository=InMemoryCaseRepository(),
        risk_engine=RiskEngine(),
        prompt_guard=PromptGuard(),
        output_guard=OutputGuard(),
        audit_service=AuditService(),
    )


def get_approval_service() -> ApprovalService:
    return ApprovalService(audit_service=AuditService())

