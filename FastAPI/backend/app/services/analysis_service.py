import asyncio
from datetime import datetime, timedelta

from app.config import get_settings
from app.core.logging_config import log_event
from app.schemas.analysis_schema import AnalysisResponse, AnalysisStatusType, ClauseAnalysis
from app.schemas.document_schema import DocumentStatusType
from app.schemas.extraction_schema import ExtractedTextLocation
from app.schemas.report_schema import ReportDifference, ReportResponse
from app.services import metrics_service, storage_service
from app.services.extraction_cache_service import get_cached_extraction
from app.services.safety_checklist_service import build_default_safety_checklist

settings = get_settings()
ANALYSIS_SEMAPHORE = asyncio.Semaphore(settings.max_concurrent_analysis_jobs)


def _find_locations_for_text(document_id: str, target_text: str) -> list[ExtractedTextLocation]:
    if not target_text:
        return []

    record = storage_service.get_document_metadata(document_id)
    cached = get_cached_extraction(
        document_id=document_id,
        content_hash=record.sha256 if record is not None else None,
    )
    if cached is None:
        return []

    compact_target = "".join(target_text.split())
    matched: list[ExtractedTextLocation] = []
    for location in cached.locations:
        compact_location = "".join(location.text.split())
        if not compact_location or location.is_redacted:
            continue
        if compact_location in compact_target or compact_target in compact_location:
            matched.append(location)

    return matched


def _generate_mock_analysis(document_id: str) -> AnalysisResponse:
    now = datetime.utcnow()
    return AnalysisResponse(
        document_id=document_id,
        status=AnalysisStatusType.completed,
        provider="clova-mock",
        extracted_text_quality=0.91,
        clauses=[
            ClauseAnalysis(
                clause_title="특약 - 원상복구 책임",
                risk_level="high",
                summary="임차인에게 과도한 원상복구 책임이 부과될 수 있습니다.",
                legal_basis="민법 및 주택임대차보호법 검토 필요",
                diff_excerpt="퇴거 시 일체의 수선비를 임차인이 부담한다",
            ),
            ClauseAnalysis(
                clause_title="보증금 반환 시점",
                risk_level="medium",
                summary="보증금 반환 시점이 모호하여 분쟁 위험이 있습니다.",
                legal_basis="임대차 종료와 동시이행 관계 검토 필요",
                diff_excerpt="임대인의 사정에 따라 반환일을 조정할 수 있다",
            ),
        ],
        retry_count=0,
        max_retry_count=settings.analysis_retry_attempts,
        processing_started_at=now,
        processing_finished_at=now,
    )


async def run_analysis_with_retry(
    *,
    document_id: str,
    request_id: str,
) -> AnalysisResponse:
    async with ANALYSIS_SEMAPHORE:
        storage_service.set_processing_state(
            document_id,
            status=DocumentStatusType.analysis_pending,
            analysis_status=AnalysisStatusType.processing.value,
        )

        for attempt in range(1, settings.analysis_retry_attempts + 1):
            started_at = datetime.utcnow()
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(_generate_mock_analysis, document_id),
                    timeout=settings.analysis_timeout_seconds,
                )
                finished_at = datetime.utcnow()
                response.retry_count = attempt - 1
                response.max_retry_count = settings.analysis_retry_attempts
                response.processing_started_at = started_at
                response.processing_finished_at = finished_at
                storage_service.mark_document_completed(
                    document_id,
                    status=DocumentStatusType.analysis_completed,
                    analysis_status=AnalysisStatusType.completed.value,
                    extracted_text_quality=response.extracted_text_quality,
                )
                metrics_service.record_metric("AnalysisSuccessCount")
                log_event(
                    "analysis_completed",
                    event="analysis_completed",
                    request_id=request_id,
                    document_id=document_id,
                    retry_count=attempt - 1,
                )
                return response
            except Exception as exc:
                next_retry_at = None
                if attempt < settings.analysis_retry_attempts:
                    next_retry_at = datetime.utcnow() + timedelta(
                        seconds=settings.retry_backoff_seconds * attempt
                    )
                storage_service.record_retry_attempt(
                    document_id,
                    attempt=attempt,
                    max_attempts=settings.analysis_retry_attempts,
                    error_message=str(exc),
                    next_retry_at=next_retry_at,
                )
                metrics_service.record_metric("AnalysisRetryCount")
                log_event(
                    "analysis_attempt_failed",
                    event="analysis_attempt_failed",
                    request_id=request_id,
                    document_id=document_id,
                    retry_count=attempt,
                    max_retry_count=settings.analysis_retry_attempts,
                )
                if attempt >= settings.analysis_retry_attempts:
                    storage_service.mark_document_failed(
                        document_id,
                        status=DocumentStatusType.failed,
                        analysis_status=AnalysisStatusType.failed.value,
                        error_message=str(exc),
                    )
                    metrics_service.record_metric("AnalysisFailureCount")
                    raise
                await asyncio.sleep(settings.retry_backoff_seconds * attempt)

    raise RuntimeError("Analysis did not complete.")


def create_mock_report(document_id: str) -> ReportResponse:
    repair_text = "퇴거 시 일체의 수선비를 임차인이 부담한다"
    deposit_text = "임대인의 사정에 따라 반환일을 조정할 수 있다"

    return ReportResponse(
        document_id=document_id,
        report_id=f"report-{document_id}",
        summary="계약서 특약과 보증금 반환 조건에서 표준 계약서와 다른 위험 문구가 확인되었습니다.",
        risk_overview="고위험 1건, 중위험 1건이 탐지되었습니다.",
        differences=[
            ReportDifference(
                category="특약",
                original_text=repair_text,
                standard_text="통상 사용으로 인한 마모를 제외한 수선 범위를 명확히 정한다",
                risk_level="high",
                highlight_color="red",
                locations=_find_locations_for_text(document_id, repair_text),
                special_term_explanation=(
                    "원상복구와 수선비 부담 범위가 과도하면 임차인에게 예상 밖의 비용이 "
                    "전가될 수 있으므로 부담 주체와 한도를 명확히 확인해야 합니다."
                ),
            ),
            ReportDifference(
                category="보증금 반환",
                original_text=deposit_text,
                standard_text="임대차 종료와 동시에 보증금을 반환한다",
                risk_level="medium",
                highlight_color="orange",
                locations=_find_locations_for_text(document_id, deposit_text),
                special_term_explanation=(
                    "보증금 반환 시점이 모호하면 퇴거 후 반환 지연이나 공제 분쟁이 생길 수 "
                    "있으므로 반환일과 공제 조건을 계약서에 구체적으로 적어야 합니다."
                ),
            ),
        ],
        recommended_actions=[
            "특약의 수선비 부담 범위와 한도를 구체적으로 수정하세요.",
            "보증금 반환일을 계약 종료일 또는 명도일과 명확히 연결해 적으세요.",
        ],
        safety_checklist=build_default_safety_checklist(),
    )
