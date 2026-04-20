from pydantic import BaseModel, Field


class ReportDifference(BaseModel):
    category: str
    original_text: str
    standard_text: str
    risk_level: str
    highlight_color: str


class ReportResponse(BaseModel):
    document_id: str
    report_id: str
    summary: str
    risk_overview: str
    differences: list[ReportDifference] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
