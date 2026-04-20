from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.sql import func

from app.db.base import Base


class DocumentMetadataModel(Base):
    __tablename__ = "document_metadata"

    document_id = Column(String, primary_key=True, index=True)
    request_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=True, index=True)

    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    sha256 = Column(String, nullable=False)
    content_type = Column(String, nullable=False)
    source = Column(String, nullable=False)

    status = Column(String, nullable=False, index=True)
    ocr_engine = Column(String, nullable=False)
    analysis_provider = Column(String, nullable=False)
    analysis_status = Column(String, nullable=False, index=True)
    report_status = Column(String, nullable=False)

    retry_count = Column(Integer, nullable=False, default=0)
    max_retry_count = Column(Integer, nullable=False, default=3)

    last_error = Column(Text, nullable=True)
    last_error_at = Column(DateTime, nullable=True)
    next_retry_at = Column(DateTime, nullable=True)

    processing_started_at = Column(DateTime, nullable=True)
    processing_finished_at = Column(DateTime, nullable=True)

    extracted_text_quality = Column(Float, nullable=True)
    deletion_scheduled_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
