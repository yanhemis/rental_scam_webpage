from pydantic import BaseModel, Field

from app.schemas.extraction_schema import ExtractedTextLocation


class SafetyChecklistItem(BaseModel):
    id: str
    label: str
    description: str
    why_it_matters: str
    official_url: str | None = None
    action_label: str | None = None
    priority: str = "medium"
    stage: str = "before_contract"
    status: str = "unchecked"


class SafetyChecklistGroup(BaseModel):
    stage: str
    title: str
    items: list[SafetyChecklistItem] = Field(default_factory=list)


class ReportDifference(BaseModel):
    category: str
    original_text: str
    standard_text: str
    risk_level: str
    highlight_color: str
    locations: list[ExtractedTextLocation] = Field(default_factory=list)
    special_term_explanation: str | None = None


class ReportResponse(BaseModel):
    document_id: str
    report_id: str
    summary: str
    risk_overview: str
    differences: list[ReportDifference] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    safety_checklist: list[SafetyChecklistGroup] = Field(default_factory=list)
