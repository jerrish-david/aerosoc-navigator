from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.api.schemas.alerts import AlertCreateRequest, AlertCreateResponse
from app.api.schemas.cases import CaseDetailResponse, CaseTriageResponse
from app.domain.entities.alert import Alert
from app.domain.entities.case import Case
from app.domain.policies.approval_policy import requires_human_approval
from app.rag.retriever import HybridRetriever
from app.repositories.interfaces.alert_repository import AlertRepository
from app.repositories.interfaces.case_repository import CaseRepository
from app.security.audit import AuditService
from app.security.output_guard import OutputGuard
from app.security.prompt_guard import PromptGuard
from app.services.risk_engine import RiskEngine


class TriageService:
    def __init__(
        self,
        alert_repository: AlertRepository,
        case_repository: CaseRepository,
        risk_engine: RiskEngine,
        prompt_guard: PromptGuard,
        output_guard: OutputGuard,
        audit_service: AuditService,
    ) -> None:
        self._alert_repository = alert_repository
        self._case_repository = case_repository
        self._risk_engine = risk_engine
        self._prompt_guard = prompt_guard
        self._output_guard = output_guard
        self._audit_service = audit_service
        self._retriever = HybridRetriever()

    def ingest_alert(self, payload: AlertCreateRequest) -> AlertCreateResponse:
        alert = Alert(
            id=uuid4(),
            source=payload.source,
            external_id=payload.external_id,
            severity=payload.severity,
            detected_at=payload.detected_at,
            raw_payload=payload.raw_payload,
            asset_id=payload.asset_id,
        )
        self._alert_repository.save(alert)

        priority_score = self._risk_engine.calculate(base_score=7.0, asset_criticality=4).total
        case = Case(
            id=uuid4(),
            title=f"{payload.source} alert {payload.external_id}",
            status="open",
            priority_score=priority_score,
        )
        self._case_repository.save(case)
        self._audit_service.record(
            actor="system",
            action="alert_ingested",
            target_type="alert",
            target_id=str(alert.id),
            correlation_id=str(case.id),
        )
        return AlertCreateResponse(
            alert_id=alert.id,
            case_id=case.id,
            status="created",
            message="Alert stored and case created for analyst triage.",
        )

    def get_case_detail(self, case_id: UUID) -> CaseDetailResponse:
        case = self._case_repository.get(case_id)
        if case is None:
            # Pseudocode: replace with repository-backed 404 behavior.
            case = Case(
                id=case_id,
                title="Placeholder case for scaffold",
                status="open",
                priority_score=8.2,
                confidence_score=0.82,
            )
        return CaseDetailResponse(
            case_id=case.id,
            title=case.title,
            status=case.status,
            priority_score=case.priority_score,
            confidence_score=case.confidence_score,
        )

    def generate_triage(self, case_id: UUID) -> CaseTriageResponse:
        evidence = self._retriever.retrieve(query=f"case:{case_id}", role="soc_analyst")
        sanitized_excerpts = [self._prompt_guard.sanitize(item.excerpt) for item in evidence]

        # Pseudocode:
        # 1. Build a structured prompt with alert facts, asset metadata, and sanitized evidence.
        # 2. Send to Azure OpenAI with a schema-constrained response format.
        # 3. Parse fields such as summary, recommendation, ATT&CK techniques, and citations.
        # 4. Reject outputs with unsupported claims or insufficient evidence coverage.
        recommendation = (
            "Investigate the affected endpoint, validate process lineage, and escalate for containment "
            "if malicious execution is confirmed."
        )
        citations = [item.source_id for item in evidence]
        confidence_score = 0.84 if sanitized_excerpts else 0.40

        self._output_guard.validate(
            recommendation=recommendation,
            citations=citations,
            confidence_score=confidence_score,
        )
        requires_approval = requires_human_approval(priority_score=8.2, recommendation=recommendation)
        self._audit_service.record(
            actor="system",
            action="triage_generated",
            target_type="case",
            target_id=str(case_id),
            correlation_id=str(uuid4()),
        )
        return CaseTriageResponse(
            case_id=case_id,
            recommendation=recommendation,
            confidence_score=confidence_score,
            citations=citations,
            requires_approval=requires_approval,
        )

