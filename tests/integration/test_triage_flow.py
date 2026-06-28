from datetime import UTC, datetime

from app.api.schemas.alerts import AlertCreateRequest
from app.api.deps.services import get_triage_service


def test_ingest_then_triage_generates_citation_backed_output() -> None:
    service = get_triage_service()
    created = service.ingest_alert(
        AlertCreateRequest(
            source="mock-siem",
            external_id="alert-001",
            severity="high",
            detected_at=datetime.now(UTC),
            raw_payload={"process_name": "powershell.exe"},
        )
    )
    triage = service.generate_triage(created.case_id)
    assert triage.citations
    assert triage.confidence_score >= 0.70

