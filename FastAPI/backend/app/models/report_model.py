from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class AnalysisStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


@dataclass(slots=True)
class ClauseFinding:
    title: str
    risk_level: RiskLevel
    summary: str
    legal_basis: str


@dataclass(slots=True)
class AnalysisResult:
    document_id: str
    status: AnalysisStatus
    findings: list[ClauseFinding] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
