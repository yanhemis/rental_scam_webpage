from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class DocumentSource(str, Enum):
    pdf = "pdf"
    mobile_scan = "mobile_scan"
    mobile_gallery = "mobile_gallery"


class DocumentStatus(str, Enum):
    uploaded = "uploaded"
    text_extracted = "text_extracted"
    analysis_pending = "analysis_pending"
    analysis_completed = "analysis_completed"
    report_ready = "report_ready"
    scheduled_for_deletion = "scheduled_for_deletion"
    deleted = "deleted"


@dataclass(slots=True)
class ContractDocument:
    document_id: str
    owner_id: str | None
    file_name: str
    file_path: str
    sha256: str
    content_type: str
    source: DocumentSource
    status: DocumentStatus
    extracted_text: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
