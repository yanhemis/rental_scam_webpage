from typing import Union, Optional
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from app.schemas.extraction_schema import ExtractedTextLocation, RedactionMetrics, RedactionTarget


class ContractDocumentType(str, Enum):
    jeonse = "jeonse"
    monthly_rent = "monthly_rent"
    mixed_rent = "mixed_rent"
    sale = "sale"
    unknown = "unknown"


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


class ContractFieldEvidence(BaseModel):
    page_number: int
    bbox: list[float] = Field(default_factory=list)
    coordinate_system: str = "source"
    span_ids: list[str] = Field(default_factory=list)
    text: str = ""
    label_text: Optional[str] = None
    value_text: Optional[str] = None
    label_bbox: Optional[list[float]] = None
    value_bbox: Optional[list[float]] = None
    match_confidence: float = 0.0
    ocr_confidence: Optional[float] = None


class ContractFieldValue(BaseModel):
    value: Optional[Union[str, int, float, bool, list[str]]] = None
    display_value: str = "확인 필요"
    confidence: float = 0.0
    needs_review: bool = True
    evidence: list[ContractFieldEvidence] = Field(default_factory=list)


class ContractFieldProfile(BaseModel):
    document_type: ContractDocumentType = ContractDocumentType.unknown
    label: str = "모름"
    required_fields: list[str] = Field(default_factory=list)
    likely_fields: list[str] = Field(default_factory=list)


class ContractFieldExtractionResult(BaseModel):
    profile: ContractFieldProfile
    fields: dict[str, ContractFieldValue] = Field(default_factory=dict)
    field_groups: dict[str, dict[str, ContractFieldValue]] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)
    low_confidence_fields: list[str] = Field(default_factory=list)
    needs_review: bool = True


class DocumentPreviewPage(BaseModel):
    page_number: int
    width: int
    height: int
    image_data_url: str
    coordinate_system: str = "source"


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
    contract_fields: Optional[ContractFieldExtractionResult] = None
    preview_pages: list[DocumentPreviewPage] = Field(default_factory=list)
    text_locations: list[ExtractedTextLocation] = Field(default_factory=list)
    redactions: list[RedactionTarget] = Field(default_factory=list)
    redaction_metrics: RedactionMetrics = Field(default_factory=RedactionMetrics)
    retry_count: int
    max_retry_count: int
    deletion_scheduled_at: Optional[datetime] = None


class DocumentMetadataRecord(BaseModel):
    document_id: str
    request_id: str
    user_id: Optional[str] = None
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
    last_error: Optional[str] = None
    last_error_at: Optional[datetime] = None
    next_retry_at: Optional[datetime] = None
    processing_started_at: Optional[datetime] = None
    processing_finished_at: Optional[datetime] = None
    extracted_text_quality: Optional[float] = None
    deletion_scheduled_at: Optional[datetime] = None
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
    status: Optional[DocumentStatusType] = None
    analysis_provider: Optional[str] = None
    analysis_status: Optional[str] = None
    report_status: Optional[str] = None
    user_id: Optional[str] = None
    retry_count: Optional[int] = None
    last_error: Optional[str] = None
    extracted_text_quality: Optional[float] = None
