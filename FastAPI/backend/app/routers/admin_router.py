from fastapi import APIRouter, HTTPException, Query, Request, status

from app.core.logging_config import get_request_id, log_event
from app.schemas.admin_schema import (
    AdminDashboardSummary,
    AdminDocumentListResponse,
    AdminRetryResponse,
)
from app.schemas.document_schema import (
    DocumentMetadataRecord,
    DocumentStatusType,
    DocumentStatusUpdateRequest,
)
from app.services import extract_service, metrics_service, storage_service
from app.services.analysis_service import run_analysis_with_retry
from typing import Optional

router = APIRouter(prefix="/admin", tags=["admin"])


def _filter_documents(
    records: list[DocumentMetadataRecord],
    *,
    status_filter: Optional[DocumentStatusType],
    analysis_status: Optional[str],
    has_error: Optional[bool],
    source: Optional[str],
    user_id: Optional[str],
) -> list[DocumentMetadataRecord]:
    filtered = records

    if status_filter is not None:
        filtered = [item for item in filtered if item.status == status_filter]
    if analysis_status is not None:
        filtered = [item for item in filtered if item.analysis_status == analysis_status]
    if has_error is not None:
        filtered = [item for item in filtered if (item.last_error is not None) == has_error]
    if source is not None:
        filtered = [item for item in filtered if item.source.value == source]
    if user_id is not None:
        filtered = [item for item in filtered if item.user_id == user_id]

    return filtered


@router.get("/documents", response_model=AdminDocumentListResponse)
async def list_admin_documents(
    status_filter: Optional[DocumentStatusType] = Query(default=None, alias="status"),
    analysis_status: Optional[str] = Query(default=None),
    has_error: Optional[bool] = Query(default=None),
    source: Optional[str] = Query(default=None),
    user_id: Optional[str] = Query(default=None),
):
    result = storage_service.list_document_metadata()
    filtered = _filter_documents(
        result.items,
        status_filter=status_filter,
        analysis_status=analysis_status,
        has_error=has_error,
        source=source,
        user_id=user_id,
    )
    return AdminDocumentListResponse(items=filtered, total=len(filtered))


@router.get("/documents/{document_id}", response_model=DocumentMetadataRecord)
async def get_admin_document_detail(document_id: str):
    record = storage_service.get_document_metadata(document_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="문서를 찾을 수 없습니다.",
        )
    return record


@router.get("/dashboard/summary", response_model=AdminDashboardSummary)
async def get_admin_dashboard_summary():
    result = storage_service.list_document_metadata()
    items = result.items

    total_quality = sum(item.extracted_text_quality or 0.0 for item in items)
    quality_count = sum(1 for item in items if item.extracted_text_quality is not None)

    return AdminDashboardSummary(
        total_documents=len(items),
        uploaded_documents=sum(1 for item in items if item.status == DocumentStatusType.uploaded),
        text_extracted_documents=sum(
            1 for item in items if item.status == DocumentStatusType.text_extracted
        ),
        analysis_pending_documents=sum(
            1 for item in items if item.status == DocumentStatusType.analysis_pending
        ),
        analysis_completed_documents=sum(
            1 for item in items if item.status == DocumentStatusType.analysis_completed
        ),
        failed_documents=sum(1 for item in items if item.status == DocumentStatusType.failed),
        documents_with_errors=sum(1 for item in items if item.last_error is not None),
        documents_scheduled_for_deletion=sum(
            1 for item in items if item.deletion_scheduled_at is not None
        ),
        average_extracted_text_quality=round(total_quality / quality_count, 3)
        if quality_count
        else 0.0,
        total_retry_count=sum(item.retry_count for item in items),
    )


@router.post("/documents/{document_id}/retry-ocr", response_model=AdminRetryResponse)
async def retry_document_ocr(request: Request, document_id: str):
    record = storage_service.get_document_metadata(document_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="문서를 찾을 수 없습니다.",
        )

    request_id = getattr(request.state, "request_id", get_request_id())
    extracted_text, quality, retry_count = await extract_service.extract_text_with_retry(
        record.file_path,
        record.content_type,
        document_id=document_id,
        request_id=request_id,
    )

    storage_service.update_document_metadata(
        document_id,
        DocumentStatusUpdateRequest(
            status=DocumentStatusType.text_extracted,
            retry_count=retry_count,
            extracted_text_quality=quality,
        ),
    )
    metrics_service.record_metric("AdminOCRRetryTriggered")
    log_event(
        "admin_ocr_retry_completed",
        event="admin_ocr_retry_completed",
        request_id=request_id,
        document_id=document_id,
        retry_count=retry_count,
    )
    return AdminRetryResponse(
        document_id=document_id,
        action="retry_ocr",
        status="completed",
        retry_count=retry_count,
        message=f"OCR 재처리가 완료되었습니다. 추출 길이: {len(extracted_text)}",
    )


@router.post("/documents/{document_id}/retry-analysis", response_model=AdminRetryResponse)
async def retry_document_analysis(request: Request, document_id: str):
    record = storage_service.get_document_metadata(document_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="문서를 찾을 수 없습니다.",
        )

    request_id = getattr(request.state, "request_id", get_request_id())
    response = await run_analysis_with_retry(document_id=document_id, request_id=request_id)
    metrics_service.record_metric("AdminAnalysisRetryTriggered")
    log_event(
        "admin_analysis_retry_completed",
        event="admin_analysis_retry_completed",
        request_id=request_id,
        document_id=document_id,
        retry_count=response.retry_count,
    )
    return AdminRetryResponse(
        document_id=document_id,
        action="retry_analysis",
        status=response.status.value,
        retry_count=response.retry_count,
        message="분석 재처리가 완료되었습니다.",
    )