import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[1] / ".env")


class Settings:
    project_name = "Jeonse Fraud Prevention API"
    project_description = (
        "FastAPI backend for contract OCR, AI analysis, and comparison reports."
    )
    version = "0.4.0"
    api_prefix = "/api"
    allowed_origins = ["*"]
    upload_dir = Path(__file__).resolve().parents[1] / "uploads"
    standard_contract_dir = Path(__file__).resolve().parents[1] / "standards"
    retention_days = 1
    clova_mock_enabled = os.getenv("CLOVA_MOCK_ENABLED", "true").lower() in {
        "1",
        "true",
        "yes",
    }
    clova_studio_api_key = os.getenv("CLOVA_STUDIO_API_KEY") or None
    clova_studio_base_url = os.getenv(
        "CLOVA_STUDIO_BASE_URL",
        "https://clovastudio.stream.ntruss.com",
    ).rstrip("/")
    clova_studio_model = os.getenv("CLOVA_STUDIO_MODEL", "HCX-007")
    clova_studio_max_input_chars = int(os.getenv("CLOVA_STUDIO_MAX_INPUT_CHARS", "24000"))
    log_level = "INFO"
    metadata_storage_backend = "dynamodb"
    dynamodb_table_name = "jeonse-document-metadata"
    metrics_namespace = "JeonseFraudPrevention"
    metrics_enabled = True
    ocr_retry_attempts = 3
    analysis_retry_attempts = 3
    retry_backoff_seconds = 1.0
    ocr_timeout_seconds = int(os.getenv("OCR_TIMEOUT_SECONDS", "90"))
    analysis_timeout_seconds = int(os.getenv("ANALYSIS_TIMEOUT_SECONDS", "25"))
    max_concurrent_ocr_jobs = 4
    max_concurrent_analysis_jobs = 4
    extraction_cache_backend = os.getenv("EXTRACTION_CACHE_BACKEND", "memory")
    extraction_cache_ttl_seconds = int(os.getenv("EXTRACTION_CACHE_TTL_SECONDS", "3600"))
    delete_raw_upload_after_ocr = os.getenv("DELETE_RAW_UPLOAD_AFTER_OCR", "true").lower() in {
        "1",
        "true",
        "yes",
    }
    privacy_template_redaction_enabled = os.getenv(
        "PRIVACY_TEMPLATE_REDACTION_ENABLED",
        "true",
    ).lower() in {"1", "true", "yes"}
    tesseract_cmd = os.getenv("TESSERACT_CMD") or None
    tesseract_lang = os.getenv("TESSERACT_LANG", "kor+eng")
    local_ocr_provider = os.getenv("LOCAL_OCR_PROVIDER", "easyocr").lower()
    # Mobile handwriting tuning: enlarge small captures, trim noisy borders,
    # and test multiple segmentation/rotation candidates.
    ocr_upscale_factor = float(os.getenv("OCR_UPSCALE_FACTOR", "2.0"))
    ocr_threshold_bias = int(os.getenv("OCR_THRESHOLD_BIAS", "165"))
    ocr_crop_border_ratio = float(os.getenv("OCR_CROP_BORDER_RATIO", "0.02"))
    pdf_ocr_render_scale = float(os.getenv("PDF_OCR_RENDER_SCALE", "2.0"))
    document_preview_max_pages = int(os.getenv("DOCUMENT_PREVIEW_MAX_PAGES", "4"))
    document_preview_jpeg_quality = int(os.getenv("DOCUMENT_PREVIEW_JPEG_QUALITY", "72"))
    ocr_rotation_angles = tuple(
        int(angle.strip())
        for angle in os.getenv("OCR_ROTATION_ANGLES", "0,-3,3").split(",")
        if angle.strip()
    )
    tesseract_psm_modes = tuple(
        int(mode.strip())
        for mode in os.getenv("TESSERACT_PSM_MODES", "6,11").split(",")
        if mode.strip()
    )
    ocr_max_candidate_images = int(os.getenv("OCR_MAX_CANDIDATE_IMAGES", "4"))
    supported_content_types = {
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/bmp",
        "image/gif",
        "image/tiff",
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
