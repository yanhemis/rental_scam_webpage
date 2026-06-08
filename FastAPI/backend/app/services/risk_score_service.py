from app.schemas.report_schema import (
    ReportDifference,
    RiskScoreBreakdown,
    SafetyChecklistGroup,
)

BASE_RISK_SCORE = 20
RISK_LEVEL_DELTAS = {
    "critical": 16,
    "high": 8,
    "medium": 4,
    "low": 2,
    "info": 0,
}


def risk_delta_for_level(risk_level: str) -> int:
    return RISK_LEVEL_DELTAS.get(risk_level, 0)


def calculate_risk_score(
    *,
    differences: list[ReportDifference],
    safety_checklist: list[SafetyChecklistGroup],
) -> RiskScoreBreakdown:
    special_terms_delta = sum(item.risk_score_delta for item in differences)
    checklist_reduction = sum(
        item.risk_reduction_points
        for group in safety_checklist
        for item in group.items
        if item.status == "completed"
    )
    final_score = max(
        0,
        min(100, BASE_RISK_SCORE + special_terms_delta - checklist_reduction),
    )
    return RiskScoreBreakdown(
        base_score=BASE_RISK_SCORE,
        special_terms_delta=special_terms_delta,
        checklist_reduction=checklist_reduction,
        final_score=final_score,
        risk_level=_risk_level_for_score(final_score),
    )


def _risk_level_for_score(score: int) -> str:
    if score >= 70:
        return "danger"
    if score >= 35:
        return "warning"
    if score >= 20:
        return "caution"
    return "normal"
