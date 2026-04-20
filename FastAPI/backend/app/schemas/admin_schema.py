from pydantic import BaseModel, Field

from app.schemas.document_schema import DocumentMetadataRecord


class AdminDashboardSummary(BaseModel):
    total_documents: int = 0
    uploaded_documents: int = 0
    text_extracted_documents: int = 0
    analysis_pending_documents: int = 0
    analysis_completed_documents: int = 0
    failed_documents: int = 0
    documents_with_errors: int = 0
    documents_scheduled_for_deletion: int = 0
    average_extracted_text_quality: float = 0.0
    total_retry_count: int = 0


class AdminDocumentListResponse(BaseModel):
    items: list[DocumentMetadataRecord] = Field(default_factory=list)
    total: int = 0


class AdminRetryResponse(BaseModel):
    document_id: str
    action: str
    status: str
    retry_count: int
    message: str
