import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.session import SessionLocal
from app.models.document_metadata_model import DocumentMetadataModel
from app.schemas.contract_extract_schema import ExtractedContractInfo
from app.schemas.document_schema import (
    DocumentMetadataListResponse,
    DocumentMetadataRecord,
    DocumentMetadataSyncResponse,
    DocumentStatusType,
    DocumentStatusUpdateRequest,
)

settings = get_settings()


def _db_record_to_schema(row: DocumentMetadataModel) -> DocumentMetadataRecord:
    return DocumentMetadataRecord(
        document_id=row.document_id,
        request_id=row.request_id,
        user_id=row.user_id,
        file_name=row.file_name,
        file_path=row.file_path,
        sha256=row.sha256,
        content_type=row.content_type,
        source=row.source,
        status=row.status,
        ocr_engine=row.ocr_engine,
        analysis_provider=row.analysis_provider,
        analysis_status=row.analysis_status,
        report_status=row.report_status,
        retry_count=row.retry_count,
        max_retry_count=row.max_retry_count,
        last_error=row.last_error,
        last_error_at=row.last_error_at,
        next_retry_at=row.next_retry_at,
        processing_started_at=row.processing_started_at,
        processing_finished_at=row.processing_finished_at,
        extracted_text_quality=row.extracted_text_quality,
        deletion_scheduled_at=row.deletion_scheduled_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _get_db() -> Session:
    return SessionLocal()


def build_deletion_schedule(from_time: Optional[datetime] = None) -> datetime:
    base_time = from_time or datetime.utcnow()
    return base_time + timedelta(days=settings.retention_days)


def save_document_metadata(record: DocumentMetadataRecord) -> DocumentMetadataRecord:
    db = _get_db()
    try:
        row = DocumentMetadataModel(
            document_id=record.document_id,
            request_id=record.request_id,
            user_id=record.user_id,
            file_name=record.file_name,
            file_path=record.file_path,
            sha256=record.sha256,
            content_type=record.content_type,
            source=record.source,
            status=record.status,
            ocr_engine=record.ocr_engine,
            analysis_provider=record.analysis_provider,
            analysis_status=record.analysis_status,
            report_status=record.report_status,
            retry_count=record.retry_count,
            max_retry_count=record.max_retry_count,
            last_error=record.last_error,
            last_error_at=record.last_error_at,
            next_retry_at=record.next_retry_at,
            processing_started_at=record.processing_started_at,
            processing_finished_at=record.processing_finished_at,
            extracted_text_quality=record.extracted_text_quality,
            deletion_scheduled_at=record.deletion_scheduled_at,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return _db_record_to_schema(row)
    finally:
        db.close()


def get_document_metadata(document_id: str) -> Optional[DocumentMetadataRecord]:
    db = _get_db()
    try:
        row = db.query(DocumentMetadataModel).filter(
            DocumentMetadataModel.document_id == document_id
        ).first()
        if row is None:
            return None
        return _db_record_to_schema(row)
    finally:
        db.close()


def list_document_metadata() -> DocumentMetadataListResponse:
    db = _get_db()
    try:
        rows = db.query(DocumentMetadataModel).order_by(desc(DocumentMetadataModel.created_at)).all()
        items = [_db_record_to_schema(row) for row in rows]
        return DocumentMetadataListResponse(items=items, total=len(items))
    finally:
        db.close()


def replace_document_metadata(record: DocumentMetadataRecord) -> DocumentMetadataRecord:
    db = _get_db()
    try:
        row = db.query(DocumentMetadataModel).filter(
            DocumentMetadataModel.document_id == record.document_id
        ).first()

        if row is None:
            row = DocumentMetadataModel(document_id=record.document_id)
            db.add(row)

        row.request_id = record.request_id
        row.user_id = record.user_id
        row.file_name = record.file_name
        row.file_path = record.file_path
        row.sha256 = record.sha256
        row.content_type = record.content_type
        row.source = record.source
        row.status = record.status
        row.ocr_engine = record.ocr_engine
        row.analysis_provider = record.analysis_provider
        row.analysis_status = record.analysis_status
        row.report_status = record.report_status
        row.retry_count = record.retry_count
        row.max_retry_count = record.max_retry_count
        row.last_error = record.last_error
        row.last_error_at = record.last_error_at
        row.next_retry_at = record.next_retry_at
        row.processing_started_at = record.processing_started_at
        row.processing_finished_at = record.processing_finished_at
        row.extracted_text_quality = record.extracted_text_quality
        row.deletion_scheduled_at = record.deletion_scheduled_at
        row.created_at = record.created_at
        row.updated_at = record.updated_at

        db.commit()
        db.refresh(row)
        return _db_record_to_schema(row)
    finally:
        db.close()


def update_document_metadata(
    document_id: str,
    payload: DocumentStatusUpdateRequest,
) -> Optional[DocumentMetadataRecord]:
    record = get_document_metadata(document_id)
    if record is None:
        return None

    update_data = record.model_dump()

    if payload.status is not None:
        update_data["status"] = payload.status
    if payload.analysis_status is not None:
        update_data["analysis_status"] = payload.analysis_status
    if payload.report_status is not None:
        update_data["report_status"] = payload.report_status
    if payload.user_id is not None:
        update_data["user_id"] = payload.user_id
    if payload.retry_count is not None:
        update_data["retry_count"] = payload.retry_count
    if payload.last_error is not None:
        update_data["last_error"] = payload.last_error
        update_data["last_error_at"] = datetime.utcnow()
    if payload.extracted_text_quality is not None:
        update_data["extracted_text_quality"] = payload.extracted_text_quality

    update_data["updated_at"] = datetime.utcnow()

    updated_record = DocumentMetadataRecord(**update_data)
    return replace_document_metadata(updated_record)


def set_processing_state(
    document_id: str,
    *,
    status: Optional[DocumentStatusType] = None,
    analysis_status: Optional[str] = None,
) -> Optional[DocumentMetadataRecord]:
    record = get_document_metadata(document_id)
    if record is None:
        return None

    updated_record = record.model_copy(
        update={
            "status": status or record.status,
            "analysis_status": analysis_status or record.analysis_status,
            "processing_started_at": datetime.utcnow(),
            "processing_finished_at": None,
            "updated_at": datetime.utcnow(),
        }
    )
    return replace_document_metadata(updated_record)


def record_retry_attempt(
    document_id: str,
    *,
    attempt: int,
    max_attempts: int,
    error_message: str,
    next_retry_at: Optional[datetime],
) -> Optional[DocumentMetadataRecord]:
    record = get_document_metadata(document_id)
    if record is None:
        return None

    updated_record = record.model_copy(
        update={
            "retry_count": attempt,
            "max_retry_count": max_attempts,
            "last_error": error_message,
            "last_error_at": datetime.utcnow(),
            "next_retry_at": next_retry_at,
            "updated_at": datetime.utcnow(),
        }
    )
    return replace_document_metadata(updated_record)


def mark_document_completed(
    document_id: str,
    *,
    status: DocumentStatusType,
    analysis_status: Optional[str] = None,
    extracted_text_quality: Optional[float] = None,
) -> Optional[DocumentMetadataRecord]:
    record = get_document_metadata(document_id)
    if record is None:
        return None

    updated_record = record.model_copy(
        update={
            "status": status,
            "analysis_status": analysis_status or record.analysis_status,
            "processing_finished_at": datetime.utcnow(),
            "next_retry_at": None,
            "last_error": None,
            "extracted_text_quality": extracted_text_quality,
            "updated_at": datetime.utcnow(),
        }
    )
    return replace_document_metadata(updated_record)


def mark_document_failed(
    document_id: str,
    *,
    status: DocumentStatusType,
    analysis_status: Optional[str],
    error_message: str,
) -> Optional[DocumentMetadataRecord]:
    record = get_document_metadata(document_id)
    if record is None:
        return None

    updated_record = record.model_copy(
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
    return replace_document_metadata(updated_record)


def mark_document_deleted(document_id: str) -> Optional[DocumentMetadataRecord]:
    record = get_document_metadata(document_id)
    if record is None:
        return None

    updated_record = record.model_copy(
        update={
            "status": DocumentStatusType.deleted,
            "updated_at": datetime.utcnow(),
        }
    )
    return replace_document_metadata(updated_record)


def build_dynamodb_item(record: DocumentMetadataRecord) -> dict[str, object]:
    return {
        "document_id": record.document_id,
        "request_id": record.request_id,
        "status": record.status,
        "analysis_status": record.analysis_status,
    }


def build_document_sync_payload(document_id: str) -> Optional[DocumentMetadataSyncResponse]:
    record = get_document_metadata(document_id)
    if record is None:
        return None

    return DocumentMetadataSyncResponse(
        document_id=document_id,
        storage_target="postgresql",
        payload=build_dynamodb_item(record),
    )


def _safe_document_id(document_id: str) -> str:
    safe_id = "".join(
        char if char.isalnum() or char in {"-", "_"} else "_"
        for char in document_id
    ).strip("_")
    if not safe_id:
        raise ValueError("document_id is required")
    return safe_id


def _artifact_dir() -> Path:
    artifact_dir = settings.upload_dir / "derived"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    return artifact_dir


def _artifact_path(document_id: str, suffix: str) -> Path:
    return _artifact_dir() / f"{_safe_document_id(document_id)}{suffix}"


def save_extracted_text(document_id: str, extracted_text: str) -> Path:
    path = _artifact_path(document_id, ".ocr.txt")
    path.write_text(extracted_text or "", encoding="utf-8")
    return path


def get_extracted_text(document_id: str) -> Optional[str]:
    path = _artifact_path(document_id, ".ocr.txt")
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def save_contract_extraction(result: ExtractedContractInfo) -> Path:
    if result.document_id is None:
        raise ValueError("document_id is required to store extracted contract fields")
    path = _artifact_path(result.document_id, ".contract_fields.json")
    path.write_text(
        json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def get_contract_extraction(document_id: str) -> Optional[ExtractedContractInfo]:
    path = _artifact_path(document_id, ".contract_fields.json")
    if not path.exists():
        return None
    return ExtractedContractInfo(**json.loads(path.read_text(encoding="utf-8")))
