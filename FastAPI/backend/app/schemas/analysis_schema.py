from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class AnalysisStatusType(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class AnalysisRequest(BaseModel):
    document_id: str
    standard_contract_type: str = Field(default="jeonse_standard_v1")
    include_legal_basis: bool = True


class ClauseAnalysis(BaseModel):
    clause_title: str
    risk_level: str
    summary: str
    legal_basis: str
    diff_excerpt: str


class AnalysisResponse(BaseModel):
    document_id: str
    status: AnalysisStatusType
    provider: str
    extracted_text_quality: float
    clauses: list[ClauseAnalysis]
    retry_count: int = 0
    max_retry_count: int = 0
    processing_started_at: datetime | None = None
    processing_finished_at: datetime | None = None
