import asyncio
from datetime import datetime, timedelta
from pathlib import Path

from app.config import get_settings
from app.core.logging_config import log_event
from app.services import metrics_service, storage_service
from app.services.image_service import extract_text_from_image
from app.utils.pdf_utils import extract_text_from_pdf
from typing import Optional, Union

settings = get_settings()
OCR_SEMAPHORE = asyncio.Semaphore(settings.max_concurrent_ocr_jobs)


def _extract_text_once(file_path: Union[str, Path], content_type: Optional[str]) -> str:
    normalized_content_type = (content_type or "").lower()

    if normalized_content_type == "application/pdf":
        return extract_text_from_pdf(file_path)

    if normalized_content_type.startswith("image/"):
        return extract_text_from_image(file_path)

    raise ValueError(f"지원하지 않는 파일 형식입니다: {content_type}")


def _estimate_text_quality(extracted_text: str) -> float:
    stripped = extracted_text.strip()
    if not stripped:
        return 0.0
    if len(stripped) >= 1000:
        return 0.96
    if len(stripped) >= 300:
        return 0.9
    return 0.8


async def extract_text_with_retry(
    file_path: Union[str, Path],
    content_type: Optional[str],
    *,
    document_id: str,
    request_id: str,
) -> tuple[str, float, int]:
    async with OCR_SEMAPHORE:
        storage_service.set_processing_state(document_id, status=None)

        for attempt in range(1, settings.ocr_retry_attempts + 1):
            try:
                extracted_text = await asyncio.wait_for(
                    asyncio.to_thread(_extract_text_once, file_path, content_type),
                    timeout=settings.ocr_timeout_seconds,
                )
                quality = _estimate_text_quality(extracted_text)
                storage_service.mark_document_completed(
                    document_id,
                    status=storage_service.get_document_metadata(document_id).status,
                    extracted_text_quality=quality,
                )
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
                )
                return extracted_text, quality, attempt - 1
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
                    storage_service.mark_document_failed(
                        document_id,
                        status=storage_service.get_document_metadata(document_id).status,
                        analysis_status=None,
                        error_message=str(exc),
                    )
                    metrics_service.record_metric(
                        "OCRFailureCount",
                        dimensions={"content_type": content_type or "unknown"},
                    )
                    raise
                await asyncio.sleep(settings.retry_backoff_seconds * attempt)