from fastapi import APIRouter

from app.schemas.report_schema import ReportResponse
from app.services.analysis_service import create_mock_report

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/{document_id}", response_model=ReportResponse)
async def get_report(document_id: str):
    return create_mock_report(document_id)
