from fastapi import APIRouter, Depends, status

from app.api.deps.services import get_triage_service
from app.api.schemas.alerts import AlertCreateRequest, AlertCreateResponse
from app.services.triage_service import TriageService


router = APIRouter()


@router.post("", response_model=AlertCreateResponse, status_code=status.HTTP_201_CREATED)
def create_alert(
    payload: AlertCreateRequest,
    triage_service: TriageService = Depends(get_triage_service),
) -> AlertCreateResponse:
    return triage_service.ingest_alert(payload)

