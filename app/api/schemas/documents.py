from uuid import UUID

from pydantic import BaseModel, Field


class DocumentUploadRequest(BaseModel):
    document_id: UUID
    title: str
    classification: str = Field(..., examples=["internal"])
    content: str


class DocumentUploadResponse(BaseModel):
    document_id: UUID
    status: str
    message: str

