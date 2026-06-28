from fastapi import APIRouter, status

from app.api.schemas.documents import DocumentUploadRequest, DocumentUploadResponse


router = APIRouter()


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_202_ACCEPTED)
def upload_document(payload: DocumentUploadRequest) -> DocumentUploadResponse:
    # Pseudocode: persist metadata, send content to chunking pipeline, await approval.
    return DocumentUploadResponse(
        document_id=payload.document_id,
        status="queued",
        message="Document accepted for security review and chunking.",
    )

