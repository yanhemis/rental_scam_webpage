from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status

from app.config import Settings
from app.core.logging_config import get_request_id, log_event
from app.dependencies import get_app_settings
from app.schemas.document_schema import (
    DocumentMetadataRecord,
    DocumentMetadataSyncResponse,
    DocumentSourceType,
    DocumentStatusType,
    DocumentStatusUpdateRequest,
    DocumentUploadResponse,
)
from app.services import extract_service, file_service, metrics_service, storage_service
from typing import Optional

router = APIRouter(tags=["documents"])


def _detect_document_source(
    content_type: Optional[str],
    source: Optional[DocumentSourceType],
) -> DocumentSourceType:
    if source is not None:
        return source
    if (content_type or "").lower() == "application/pdf":
        return DocumentSourceType.pdf
    return DocumentSourceType.mobile_scan


async def _handle_upload(
    request: Request,
    file: UploadFile,
    settings: Settings,
    source: Optional[DocumentSourceType],
    user_id: Optional[str],
) -> DocumentUploadResponse:
    request_id = getattr(request.state, "request_id", get_request_id())

    if file.content_type not in settings.supported_content_types:
        metrics_service.record_metric("UploadFailureCount")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PDF 또는 이미지 파일만 업로드 가능합니다.",
        )

    document_id = f"doc-{uuid4().hex[:12]}"
    saved_path, sha256_hash = await file_service.save_upload_file(file)
    now = datetime.utcnow()
    deletion_scheduled_at = storage_service.build_deletion_schedule(now)
    document_source = _detect_document_source(file.content_type, source)

    metadata = DocumentMetadataRecord(
        document_id=document_id,
        request_id=request_id,
        user_id=user_id,
        file_name=file.filename or "upload",
        file_path=str(saved_path),
        sha256=sha256_hash,
        content_type=file.content_type or "application/octet-stream",
        source=document_source,
        status=DocumentStatusType.uploaded,
        max_retry_count=settings.ocr_retry_attempts,
        deletion_scheduled_at=deletion_scheduled_at,
        created_at=now,
        updated_at=now,
    )
    storage_service.save_document_metadata(metadata)

    try:
        extracted_text, quality, retry_count = await extract_service.extract_text_with_retry(
            saved_path,
            file.content_type,
            document_id=document_id,
            request_id=request_id,
        )
    except ValueError as exc:
        metrics_service.record_metric("UploadFailureCount")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        metrics_service.record_metric("UploadFailureCount")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    metadata = storage_service.update_document_metadata(
        document_id,
        DocumentStatusUpdateRequest(
            status=DocumentStatusType.text_extracted,
            retry_count=retry_count,
            extracted_text_quality=quality,
        ),
    )
    metrics_service.record_metric("UploadSuccessCount")
    log_event(
        "document_uploaded",
        event="document_uploaded",
        request_id=request_id,
        document_id=document_id,
        user_id=user_id,
        content_type=metadata.content_type,
        source=metadata.source.value,
        retry_count=metadata.retry_count,
    )

    preview_text = extracted_text[:500] if extracted_text else ""
    return DocumentUploadResponse(
        request_id=request_id,
        document_id=document_id,
        file_name=metadata.file_name,
        file_path=metadata.file_path,
        sha256=metadata.sha256,
        content_type=metadata.content_type,
        source=metadata.source,
        status=metadata.status,
        text_preview=preview_text,
        full_text=extracted_text,
        retry_count=metadata.retry_count,
        max_retry_count=metadata.max_retry_count,
        deletion_scheduled_at=metadata.deletion_scheduled_at,
    )


@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    source: Optional[DocumentSourceType] = Form(default=None),
    user_id: Optional[str] = Form(default=None),
    settings: Settings = Depends(get_app_settings),
):
    return await _handle_upload(request, file, settings, source, user_id)


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document_legacy(
    request: Request,
    file: UploadFile = File(...),
    source: Optional[DocumentSourceType] = Form(default=None),
    user_id: Optional[str] = Form(default=None),
    settings: Settings = Depends(get_app_settings),
):
    return await _handle_upload(request, file, settings, source, user_id)


@router.get("/documents/metadata", response_model=list[DocumentMetadataRecord])
async def list_documents_metadata():
    result = storage_service.list_document_metadata()
    return result.items


@router.get("/documents/{document_id}/metadata", response_model=DocumentMetadataRecord)
async def get_document_metadata(document_id: str):
    record = storage_service.get_document_metadata(document_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="문서를 찾을 수 없습니다.")
    return record


@router.patch("/documents/{document_id}/metadata", response_model=DocumentMetadataRecord)
async def patch_document_metadata(
    document_id: str,
    payload: DocumentStatusUpdateRequest,
):
    record = storage_service.update_document_metadata(document_id, payload)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="문서를 찾을 수 없습니다.")

    log_event(
        "document_metadata_updated",
        event="document_metadata_updated",
        document_id=document_id,
        request_id=record.request_id,
        user_id=record.user_id,
    )
    return record


@router.get("/documents/{document_id}/sync-payload", response_model=DocumentMetadataSyncResponse)
async def get_document_sync_payload(document_id: str):
    payload = storage_service.build_document_sync_payload(document_id)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="문서를 찾을 수 없습니다.")
    return payload