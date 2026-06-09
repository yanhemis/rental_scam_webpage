import unittest
from datetime import datetime
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.document_schema import (
    DocumentMetadataRecord,
    DocumentSourceType,
    DocumentStatusType,
)
from app.schemas.extraction_schema import ExtractionResult
from app.services import analysis_service, storage_service
from app.services.extraction_cache_service import cache_extraction


class AnalysisFlowTests(unittest.TestCase):
    def test_analysis_result_is_used_by_report_and_deleted_with_document(self) -> None:
        document_id = "doc-analysis-flow-test"
        now = datetime.utcnow()
        storage_service.save_document_metadata(
            DocumentMetadataRecord(
                document_id=document_id,
                request_id="req-analysis-flow-test",
                file_name="contract.pdf",
                file_path="[raw_upload_deleted_after_ocr]",
                sha256="test-hash",
                content_type="application/pdf",
                source=DocumentSourceType.pdf,
                status=DocumentStatusType.text_extracted,
                created_at=now,
                updated_at=now,
            )
        )
        cache_extraction(
            ExtractionResult(
                document_id=document_id,
                content_hash="test-hash",
                text=(
                    "퇴거 시 일체의 수선비를 임차인이 부담한다. "
                    "임대인의 사정에 따라 반환일을 조정할 수 있다."
                ),
                quality=0.9,
                extracted_at=now,
            )
        )

        with patch.object(analysis_service.settings, "clova_mock_enabled", True):
            with TestClient(app) as client:
                analysis_response = client.post(
                    "/api/analysis/run",
                    json={"document_id": document_id},
                )
                report_response = client.get(f"/api/reports/{document_id}")
                delete_response = client.delete(f"/api/retention/documents/{document_id}")

        self.assertEqual(analysis_response.status_code, 200)
        self.assertEqual(analysis_response.json()["provider"], "clova-mock")
        self.assertEqual(report_response.status_code, 200)
        self.assertEqual(len(report_response.json()["differences"]), 2)
        self.assertTrue(delete_response.json()["analysis_cache_deleted"])
        self.assertIsNone(analysis_service.get_analysis_result(document_id))


if __name__ == "__main__":
    unittest.main()
