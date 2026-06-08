from pydantic import BaseModel, Field

from app.schemas.extraction_schema import ExtractedTextLocation


class ChecklistExternalAction(BaseModel):
    label: str
    url: str
    type: str = "external_link"
    opens_in_new_window: bool = True
    completion_hint: str | None = None


class SafetyChecklistItem(BaseModel):
    id: str
    label: str
    description: str
    why_it_matters: str
    official_url: str | None = None
    action_label: str | None = None
    external_action: ChecklistExternalAction | None = None
    priority: str = "medium"
    stage: str = "before_contract"
    status: str = "unchecked"
    risk_reduction_points: int = 0


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
    risk_score_delta: int = 0


class RiskScoreBreakdown(BaseModel):
    base_score: int
    special_terms_delta: int
    checklist_reduction: int
    final_score: int
    risk_level: str
    formula_version: str = "mvp-2026-06-09"


class ReportResponse(BaseModel):
    document_id: str
    report_id: str
    summary: str
    risk_overview: str
    risk_score: RiskScoreBreakdown
    differences: list[ReportDifference] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    safety_checklist: list[SafetyChecklistGroup] = Field(default_factory=list)
