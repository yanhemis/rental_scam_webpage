from typing import Optional
from fastapi import APIRouter, Query

from app.schemas.report_schema import ReportResponse
from app.services.analysis_service import create_report

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/{document_id}", response_model=ReportResponse)
async def get_report(
    document_id: str,
    completed_checks: Optional[list[str]] = Query(default=None),
):
    return create_report(
        document_id,
        completed_check_ids=set(completed_checks or []),
    )
