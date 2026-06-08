from datetime import datetime

from fastapi import APIRouter, HTTPException, status

from app.services import file_service, storage_service
from app.services.extraction_cache_service import purge_document_extraction

router = APIRouter(prefix="/retention", tags=["retention"])


@router.get("/documents/{document_id}")
async def get_retention_status(document_id: str):
    scheduled_at = storage_service.build_deletion_schedule()
    return {
        "document_id": document_id,
        "delete_policy": "internal_retention_policy_v1",
        "scheduled_for_deletion_at": scheduled_at.isoformat(),
        "checked_at": datetime.utcnow().isoformat(),
    }


@router.delete("/documents/{document_id}")
async def delete_document_data(document_id: str):
    record = storage_service.get_document_metadata(document_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document metadata was not found.",
        )

    file_deleted = file_service.delete_upload_file(record.file_path)
    purge_document_extraction(document_id)
    updated = storage_service.mark_document_deleted(document_id)

    return {
        "document_id": document_id,
        "delete_policy": "internal_retention_policy_v1",
        "file_deleted": file_deleted,
        "ocr_cache_deleted": True,
        "location_cache_deleted": True,
        "metadata_status": updated.status.value if updated is not None else "deleted",
        "deleted_at": datetime.utcnow().isoformat(),
    }
