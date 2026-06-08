from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ExtractionLocationSource(str, Enum):
    pdf_text = "pdf_text"
    image_ocr = "image_ocr"
    fallback_page = "fallback_page"


class MaskStyle(str, Enum):
    opaque = "opaque"
    mosaic = "mosaic"
    translucent = "translucent"


class RedactionSensitivity(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class RedactionDetectionMethod(str, Enum):
    template = "template"
    ocr_label = "ocr_label"
    regex = "regex"


class ExtractedTextLocation(BaseModel):
    span_id: str
    text: str
    page_number: int
    bbox: list[float] = Field(
        min_length=4,
        max_length=4,
        description="Bounding box as [x0, y0, x1, y1] in the source coordinate system.",
    )
    confidence: float | None = None
    source: ExtractionLocationSource
    coordinate_system: str = "source"
    is_redacted: bool = False
    redaction_type: str | None = None
    redaction_id: str | None = None


class RedactionTarget(BaseModel):
    redaction_id: str
    label_type: str
    label_text: str
    page_number: int
    label_bbox: list[float] = Field(min_length=4, max_length=4)
    value_bbox: list[float] = Field(min_length=4, max_length=4)
    coordinate_system: str = "source"
    confidence: float = 0.7
    box_confidence: float = 0.7
    text_confidence: float | None = None
    detection_method: RedactionDetectionMethod = RedactionDetectionMethod.ocr_label
    sensitivity: RedactionSensitivity = RedactionSensitivity.high
    mask_style: MaskStyle = MaskStyle.opaque
    opacity: float = Field(default=1.0, ge=0.0, le=1.0)
    needs_review: bool = False


class RedactionMetrics(BaseModel):
    total_redaction_count: int = 0
    template_redaction_count: int = 0
    ocr_label_redaction_count: int = 0
    regex_redaction_count: int = 0
    redacted_location_count: int = 0
    average_box_confidence: float = 0.0
    needs_review_count: int = 0


class ExtractionResult(BaseModel):
    document_id: str
    content_hash: str | None = None
    text: str
    quality: float
    locations: list[ExtractedTextLocation] = Field(default_factory=list)
    redactions: list[RedactionTarget] = Field(default_factory=list)
    redaction_metrics: RedactionMetrics = Field(default_factory=RedactionMetrics)
    extracted_at: datetime
    cache_hit: bool = False
