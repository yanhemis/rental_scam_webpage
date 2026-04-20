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

    # 🔽 여기 중요 (PostgreSQL 연결)
    database_url: str = "postgresql+psycopg2://postgres:1q2w3e4r!@localhost:5432/jeonse_db"

    # 🔽 이제 PostgreSQL 쓰니까 변경
    metadata_storage_backend = "postgresql"

    # 기존 설정 유지 (나중 대비)
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
