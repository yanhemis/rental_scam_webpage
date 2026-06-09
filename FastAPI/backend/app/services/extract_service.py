from typing import Union, Optional
import asyncio
from datetime import datetime, timedelta
from pathlib import Path

from app.config import get_settings
from app.core.logging_config import log_event
from app.schemas.extraction_schema import ExtractionResult
from app.services import metrics_service, storage_service
from app.services.extraction_cache_service import cache_extraction, get_cached_extraction
from app.services.image_service import extract_text_locations_from_image
from app.services.redaction_service import apply_privacy_redactions
from app.utils.pdf_utils import extract_text_locations_from_pdf

settings = get_settings()
OCR_SEMAPHORE = asyncio.Semaphore(settings.max_concurrent_ocr_jobs)


def _estimate_text_quality(extracted_text: str) -> float:
    stripped = extracted_text.strip()
    if not stripped:
        return 0.0
    if len(stripped) >= 1000:
        return 0.96
    if len(stripped) >= 300:
        return 0.9
    return 0.8


def _extract_text_once(
    file_path: Union[str, Path],
    content_type: Optional[str],
    *,
    document_id: str,
    content_hash: Optional[str],
) -> ExtractionResult:
    normalized_content_type = (content_type or "").lower()

    if normalized_content_type == "application/pdf":
        text, locations = extract_text_locations_from_pdf(file_path)
    elif normalized_content_type.startswith("image/"):
        text, locations = extract_text_locations_from_image(file_path)
    else:
        raise ValueError(f"Unsupported file content type: {content_type}")

    result = ExtractionResult(
        document_id=document_id,
        content_hash=content_hash,
        text=text,
        quality=_estimate_text_quality(text),
        locations=locations,
        extracted_at=datetime.utcnow(),
    )
    redacted_result = apply_privacy_redactions(result)
    return redacted_result.model_copy(
        update={"quality": _estimate_text_quality(redacted_result.text)}
    )


async def extract_document_with_retry(
    file_path: Union[str, Path],
    content_type: Optional[str],
    *,
    document_id: str,
    request_id: str,
    content_hash: Optional[str] = None,
) -> tuple[ExtractionResult, int]:
    async with OCR_SEMAPHORE:
        cached = get_cached_extraction(document_id=document_id, content_hash=content_hash)
        if cached is not None:
            log_event(
                "ocr_cache_hit",
                event="ocr_cache_hit",
                request_id=request_id,
                document_id=document_id,
                content_type=content_type,
            )
            return cached.model_copy(update={"document_id": document_id}), 0

        storage_service.set_processing_state(document_id, status=None)

        for attempt in range(1, settings.ocr_retry_attempts + 1):
            try:
                result = await asyncio.wait_for(
                    asyncio.to_thread(
                        _extract_text_once,
                        file_path,
                        content_type,
                        document_id=document_id,
                        content_hash=content_hash,
                    ),
                    timeout=settings.ocr_timeout_seconds,
                )
                storage_service.mark_document_completed(
                    document_id,
                    status=storage_service.get_document_metadata(document_id).status,
                    extracted_text_quality=result.quality,
                )
                cache_extraction(result)
                metrics_service.record_metric(
                    "OCRSuccessCount",
                    dimensions={"content_type": content_type or "unknown"},
                )
                log_event(
                    "ocr_completed",
                    event="ocr_completed",
                    request_id=request_id,
                    document_id=document_id,
                    retry_count=attempt - 1,
                    content_type=content_type,
                    location_count=len(result.locations),
                )
                return result, attempt - 1
            except Exception as exc:
                next_retry_at = None
                if attempt < settings.ocr_retry_attempts:
                    next_retry_at = datetime.utcnow() + timedelta(
                        seconds=settings.retry_backoff_seconds * attempt
                    )
                storage_service.record_retry_attempt(
                    document_id,
                    attempt=attempt,
                    max_attempts=settings.ocr_retry_attempts,
                    error_message=str(exc),
                    next_retry_at=next_retry_at,
                )
                metrics_service.record_metric(
                    "OCRRetryCount",
                    dimensions={"content_type": content_type or "unknown"},
                )
                log_event(
                    "ocr_attempt_failed",
                    event="ocr_attempt_failed",
                    request_id=request_id,
                    document_id=document_id,
                    retry_count=attempt,
                    max_retry_count=settings.ocr_retry_attempts,
                    content_type=content_type,
                )
                if attempt >= settings.ocr_retry_attempts:
                    record = storage_service.get_document_metadata(document_id)
                    storage_service.mark_document_failed(
                        document_id,
                        status=record.status if record is not None else storage_service.DocumentStatusType.failed,
                        analysis_status=None,
                        error_message=str(exc),
                    )
                    metrics_service.record_metric(
                        "OCRFailureCount",
                        dimensions={"content_type": content_type or "unknown"},
                    )
                    fallback_result = ExtractionResult(
                        document_id=document_id,
                        content_hash=content_hash,
                        text="",
                        quality=0.0,
                        locations=[],
                        extracted_at=datetime.utcnow(),
                    )
                    cache_extraction(fallback_result)
                    return fallback_result, attempt
           
            await asyncio.sleep(settings.retry_backoff_seconds * attempt)

    raise RuntimeError("OCR extraction did not complete.")


async def extract_text_with_retry(
    file_path: Union[str, Path],
    content_type: Optional[str],
    *,
    document_id: str,
    request_id: str,
    content_hash: Optional[str] = None,
) -> tuple[str, float, int]:
    result, retry_count = await extract_document_with_retry(
        file_path,
        content_type,
        document_id=document_id,
        request_id=request_id,
        content_hash=content_hash,
    )
    return result.text, result.quality, retry_count
