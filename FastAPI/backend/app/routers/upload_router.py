from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status

from app.config import Settings
from app.core.logging_config import get_request_id, log_event
from app.dependencies import get_app_settings
from app.schemas.document_schema import (
    ContractDocumentType,
    DocumentMetadataRecord,
    DocumentMetadataSyncResponse,
    DocumentSourceType,
    DocumentStatusType,
    DocumentStatusUpdateRequest,
    DocumentUploadResponse,
)
from app.services import (
    contract_field_service,
    extract_service,
    file_service,
    metrics_service,
    storage_service,
)

router = APIRouter(tags=["documents"])


def _detect_document_source(
    content_type: str | None,
    source: DocumentSourceType | None,
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
    source: DocumentSourceType | None,
    user_id: str | None,
    document_type: ContractDocumentType | None,
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
        extraction_result, retry_count = await extract_service.extract_document_with_retry(
            saved_path,
            file.content_type,
            document_id=document_id,
            request_id=request_id,
            content_hash=sha256_hash,
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
            extracted_text_quality=extraction_result.quality,
        ),
    )
    raw_file_deleted = False
    if settings.delete_raw_upload_after_ocr:
        raw_file_deleted = file_service.delete_upload_file(saved_path)
        if raw_file_deleted:
            metadata = metadata.model_copy(
                update={
                    "file_path": "[raw_upload_deleted_after_ocr]",
                    "updated_at": datetime.utcnow(),
                }
            )
            storage_service.replace_document_metadata(metadata)

    contract_fields = contract_field_service.extract_contract_fields(
        extraction_result.text,
        extraction_result.locations,
        document_type=document_type,
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
        raw_file_deleted=raw_file_deleted,
        redaction_count=len(extraction_result.redactions),
        document_type=contract_fields.profile.document_type.value,
        missing_field_count=len(contract_fields.missing_fields),
    )

    preview_text = extraction_result.text[:500] if extraction_result.text else ""
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
        full_text=extraction_result.text,
        contract_fields=contract_fields,
        text_locations=extraction_result.locations,
        redactions=extraction_result.redactions,
        redaction_metrics=extraction_result.redaction_metrics,
        retry_count=metadata.retry_count,
        max_retry_count=metadata.max_retry_count,
        deletion_scheduled_at=metadata.deletion_scheduled_at,
    )


@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    source: DocumentSourceType | None = Form(default=None),
    user_id: str | None = Form(default=None),
    document_type: ContractDocumentType | None = Form(default=ContractDocumentType.unknown),
    settings: Settings = Depends(get_app_settings),
):
    return await _handle_upload(request, file, settings, source, user_id, document_type)


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document_legacy(
    request: Request,
    file: UploadFile = File(...),
    source: DocumentSourceType | None = Form(default=None),
    user_id: str | None = Form(default=None),
    document_type: ContractDocumentType | None = Form(default=ContractDocumentType.unknown),
    settings: Settings = Depends(get_app_settings),
):
    return await _handle_upload(request, file, settings, source, user_id, document_type)


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
