from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from app.schemas.extraction_schema import ExtractedTextLocation, RedactionMetrics, RedactionTarget


class DocumentSourceType(str, Enum):
    pdf = "pdf"
    mobile_scan = "mobile_scan"
    mobile_gallery = "mobile_gallery"


class DocumentStatusType(str, Enum):
    uploaded = "uploaded"
    text_extracted = "text_extracted"
    analysis_pending = "analysis_pending"
    analysis_completed = "analysis_completed"
    report_ready = "report_ready"
    scheduled_for_deletion = "scheduled_for_deletion"
    deleted = "deleted"
    failed = "failed"


class DocumentUploadResponse(BaseModel):
    request_id: str
    document_id: str
    file_name: str
    file_path: str
    sha256: str
    content_type: str
    source: DocumentSourceType
    status: DocumentStatusType
    text_preview: str
    full_text: str
    text_locations: list[ExtractedTextLocation] = Field(default_factory=list)
    redactions: list[RedactionTarget] = Field(default_factory=list)
    redaction_metrics: RedactionMetrics = Field(default_factory=RedactionMetrics)
    retry_count: int
    max_retry_count: int
    deletion_scheduled_at: datetime | None = None


class DocumentMetadataRecord(BaseModel):
    document_id: str
    request_id: str
    user_id: str | None = None
    file_name: str
    file_path: str
    sha256: str
    content_type: str
    source: DocumentSourceType
    status: DocumentStatusType
    ocr_engine: str = "pytesseract"
    analysis_provider: str = "clova-mock"
    analysis_status: str = "pending"
    report_status: str = "pending"
    retry_count: int = 0
    max_retry_count: int = 0
    last_error: str | None = None
    last_error_at: datetime | None = None
    next_retry_at: datetime | None = None
    processing_started_at: datetime | None = None
    processing_finished_at: datetime | None = None
    extracted_text_quality: float | None = None
    deletion_scheduled_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class DocumentMetadataListResponse(BaseModel):
    items: list[DocumentMetadataRecord] = Field(default_factory=list)
    total: int


class DocumentMetadataSyncResponse(BaseModel):
    document_id: str
    storage_target: str
    payload: dict[str, object]


class DocumentStatusUpdateRequest(BaseModel):
    status: DocumentStatusType | None = None
    analysis_status: str | None = None
    report_status: str | None = None
    user_id: str | None = None
    retry_count: int | None = None
    last_error: str | None = None
    extracted_text_quality: float | None = None
