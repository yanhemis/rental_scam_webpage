from fastapi import APIRouter, HTTPException, Request, status

from app.core.logging_config import get_request_id
from app.schemas.analysis_schema import AnalysisRequest, AnalysisResponse
from app.services.analysis_service import run_analysis_with_retry
from app.services.storage_service import get_document_metadata

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/run", response_model=AnalysisResponse)
async def run_analysis(request: Request, payload: AnalysisRequest):
    document = get_document_metadata(payload.document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="분석할 문서를 찾을 수 없습니다.",
        )

    request_id = getattr(request.state, "request_id", get_request_id())
    return await run_analysis_with_retry(
        document_id=payload.document_id,
        request_id=request_id,
        include_legal_basis=payload.include_legal_basis,
    )
