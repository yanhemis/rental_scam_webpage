import os
from functools import lru_cache
from pathlib import Path


class Settings:
    project_name: str = "Jeonse Fraud Prevention API"
    project_description = (
        "FastAPI backend for contract OCR, AI analysis, and comparison reports."
    )
    version = "0.4.0"
    api_prefix = "/api"

    allowed_origins = ["*"]

    upload_dir = Path(__file__).resolve().parents[1] / "uploads"
    standard_contract_dir = Path(__file__).resolve().parents[1] / "standards"

    retention_days = 1
    clova_mock_enabled = True
    log_level = "INFO"

    database_url: str = "postgresql+psycopg2://postgres:1q2w3e4r!@localhost:5432/jeonse_db"
    metadata_storage_backend = "postgresql"
    dynamodb_table_name = "jeonse-document-metadata"

    metrics_namespace = "JeonseFraudPrevention"
    metrics_enabled = True

    ocr_retry_attempts = 3
    analysis_retry_attempts = 3
    retry_backoff_seconds = 1.0

    ocr_timeout_seconds = 20
    analysis_timeout_seconds = 25

    max_concurrent_ocr_jobs = 4
    max_concurrent_analysis_jobs = 4

    tesseract_cmd = os.getenv("TESSERACT_CMD") or None
    tesseract_lang = os.getenv("TESSERACT_LANG", "kor+eng")
    ocr_upscale_factor = float(os.getenv("OCR_UPSCALE_FACTOR", "2.0"))
    ocr_threshold_bias = int(os.getenv("OCR_THRESHOLD_BIAS", "165"))
    ocr_crop_border_ratio = float(os.getenv("OCR_CROP_BORDER_RATIO", "0.02"))
    ocr_rotation_angles = tuple(
        int(angle.strip())
        for angle in os.getenv("OCR_ROTATION_ANGLES", "0,-3,3,-6,6").split(",")
        if angle.strip()
    )
    tesseract_psm_modes = tuple(
        int(mode.strip())
        for mode in os.getenv("TESSERACT_PSM_MODES", "6,11,4").split(",")
        if mode.strip()
    )

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
