from datetime import datetime

from fastapi import APIRouter

from app.services.storage_service import build_deletion_schedule

router = APIRouter(prefix="/retention", tags=["retention"])


@router.get("/documents/{document_id}")
async def get_retention_status(document_id: str):
    scheduled_at = build_deletion_schedule()
    return {
        "document_id": document_id,
        "delete_policy": "internal_retention_policy_v1",
        "scheduled_for_deletion_at": scheduled_at.isoformat(),
        "checked_at": datetime.utcnow().isoformat(),
    }
