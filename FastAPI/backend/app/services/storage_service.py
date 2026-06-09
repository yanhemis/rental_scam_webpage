from datetime import datetime, timedelta

from app.config import get_settings
from app.schemas.document_schema import (
    DocumentMetadataListResponse,
    DocumentMetadataRecord,
    DocumentMetadataSyncResponse,
    DocumentStatusType,
    DocumentStatusUpdateRequest,
)

class InMemoryDocumentMetadataRepository:
    def __init__(self) -> None:
        self._store: dict[str, DocumentMetadataRecord] = {}

    def save(self, record: DocumentMetadataRecord) -> DocumentMetadataRecord:
        self._store[record.document_id] = record
        return record

    def get(self, document_id: str) -> DocumentMetadataRecord | None:
        return self._store.get(document_id)

    def list(self) -> DocumentMetadataListResponse:
        items = sorted(
            self._store.values(),
            key=lambda item: item.created_at,
            reverse=True,
        )
        return DocumentMetadataListResponse(items=items, total=len(items))


_repository = InMemoryDocumentMetadataRepository()


def build_deletion_schedule(from_time: datetime | None = None) -> datetime:
    settings = get_settings()
    base_time = from_time or datetime.utcnow()
    return base_time + timedelta(days=settings.retention_days)


def save_document_metadata(record: DocumentMetadataRecord) -> DocumentMetadataRecord:
    return _repository.save(record)


def get_document_metadata(document_id: str) -> DocumentMetadataRecord | None:
    return _repository.get(document_id)


def list_document_metadata() -> DocumentMetadataListResponse:
    return _repository.list()


def replace_document_metadata(record: DocumentMetadataRecord) -> DocumentMetadataRecord:
    return _repository.save(record)


def update_document_metadata(
    document_id: str,
    payload: DocumentStatusUpdateRequest,
) -> DocumentMetadataRecord | None:
    record = _repository.get(document_id)
    if record is None:
        return None

    updates = record.model_dump()
    if payload.status is not None:
        updates["status"] = payload.status
    if payload.analysis_provider is not None:
        updates["analysis_provider"] = payload.analysis_provider
    if payload.analysis_status is not None:
        updates["analysis_status"] = payload.analysis_status
    if payload.report_status is not None:
        updates["report_status"] = payload.report_status
    if payload.user_id is not None:
        updates["user_id"] = payload.user_id
    if payload.retry_count is not None:
        updates["retry_count"] = payload.retry_count
    if payload.last_error is not None:
        updates["last_error"] = payload.last_error
        updates["last_error_at"] = datetime.utcnow()
    if payload.extracted_text_quality is not None:
        updates["extracted_text_quality"] = payload.extracted_text_quality
    updates["updated_at"] = datetime.utcnow()

    return _repository.save(DocumentMetadataRecord(**updates))


def set_processing_state(
    document_id: str,
    *,
    status: DocumentStatusType | None = None,
    analysis_status: str | None = None,
) -> DocumentMetadataRecord | None:
    record = _repository.get(document_id)
    if record is None:
        return None

    updated = record.model_copy(
        update={
            "status": status or record.status,
            "analysis_status": analysis_status or record.analysis_status,
            "processing_started_at": datetime.utcnow(),
            "processing_finished_at": None,
            "updated_at": datetime.utcnow(),
        }
    )
    return _repository.save(updated)


def record_retry_attempt(
    document_id: str,
    *,
    attempt: int,
    max_attempts: int,
    error_message: str,
    next_retry_at: datetime | None,
) -> DocumentMetadataRecord | None:
    record = _repository.get(document_id)
    if record is None:
        return None

    updated = record.model_copy(
        update={
            "retry_count": attempt,
            "max_retry_count": max_attempts,
            "last_error": error_message,
            "last_error_at": datetime.utcnow(),
            "next_retry_at": next_retry_at,
            "updated_at": datetime.utcnow(),
        }
    )
    return _repository.save(updated)


def mark_document_completed(
    document_id: str,
    *,
    status: DocumentStatusType,
    analysis_provider: str | None = None,
    analysis_status: str | None = None,
    extracted_text_quality: float | None = None,
) -> DocumentMetadataRecord | None:
    record = _repository.get(document_id)
    if record is None:
        return None

    updated = record.model_copy(
        update={
            "status": status,
            "analysis_provider": analysis_provider or record.analysis_provider,
            "analysis_status": analysis_status or record.analysis_status,
            "processing_finished_at": datetime.utcnow(),
            "next_retry_at": None,
            "last_error": None,
            "extracted_text_quality": extracted_text_quality,
            "updated_at": datetime.utcnow(),
        }
    )
    return _repository.save(updated)


def mark_document_failed(
    document_id: str,
    *,
    status: DocumentStatusType,
    analysis_status: str | None,
    error_message: str,
) -> DocumentMetadataRecord | None:
    record = _repository.get(document_id)
    if record is None:
        return None

    updated = record.model_copy(
        update={
            "status": status,
            "analysis_status": analysis_status or record.analysis_status,
            "last_error": error_message,
            "last_error_at": datetime.utcnow(),
            "processing_finished_at": datetime.utcnow(),
            "next_retry_at": None,
            "updated_at": datetime.utcnow(),
        }
    )
    return _repository.save(updated)


def mark_document_deleted(document_id: str) -> DocumentMetadataRecord | None:
    record = _repository.get(document_id)
    if record is None:
        return None

    updated = record.model_copy(
        update={
            "status": DocumentStatusType.deleted,
            "updated_at": datetime.utcnow(),
        }
    )
    return _repository.save(updated)


def build_dynamodb_item(record: DocumentMetadataRecord) -> dict[str, object]:
    settings = get_settings()
    item = record.model_dump(mode="json")
    item["pk"] = f"DOCUMENT#{record.document_id}"
    item["sk"] = "METADATA"
    item["gsi1pk"] = f"STATUS#{record.status.value}"
    item["gsi1sk"] = record.created_at.isoformat()
    return {
        "table_name": settings.dynamodb_table_name,
        "item": item,
        "keys": {
            "pk": item["pk"],
            "sk": item["sk"],
        },
    }


def build_document_sync_payload(document_id: str) -> DocumentMetadataSyncResponse | None:
    record = _repository.get(document_id)
    if record is None:
        return None

    return DocumentMetadataSyncResponse(
        document_id=document_id,
        storage_target="dynamodb",
        payload=build_dynamodb_item(record),
    )
