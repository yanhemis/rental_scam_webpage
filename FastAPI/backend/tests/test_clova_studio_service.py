import json
import unittest
from unittest.mock import MagicMock, patch

import httpx

from app.services.clova_studio_service import ClovaStudioError, analyze_contract


class TestSettings:
    clova_studio_api_key = "nv-test-key"
    clova_studio_base_url = "https://clovastudio.stream.ntruss.com"
    clova_studio_model = "HCX-007"
    clova_studio_max_input_chars = 24000
    analysis_timeout_seconds = 25


def _mock_response(status_code: int, body: dict) -> httpx.Response:
    return httpx.Response(
        status_code,
        json=body,
        request=httpx.Request("POST", "https://clovastudio.stream.ntruss.com"),
    )


class ClovaStudioServiceTests(unittest.TestCase):
    @patch("app.services.clova_studio_service.httpx.Client")
    def test_parses_structured_analysis(self, client_class: MagicMock) -> None:
        content = {
            "clauses": [
                {
                    "clause_title": "보증금 반환 시점",
                    "risk_level": "high",
                    "summary": "반환 시점이 임대인 사정에 따라 달라질 수 있습니다.",
                    "legal_basis": "동시이행 관계 검토 필요",
                    "diff_excerpt": "임대인의 사정에 따라 반환일을 조정할 수 있다",
                }
            ]
        }
        client_class.return_value.__enter__.return_value.post.return_value = _mock_response(
            200,
            {
                "status": {"code": "20000", "message": "OK"},
                "result": {
                    "message": {
                        "role": "assistant",
                        "content": json.dumps(content, ensure_ascii=False),
                    }
                },
            },
        )

        result = analyze_contract(
            "보증금 반환 조항",
            request_id="req-test",
            settings=TestSettings(),
        )

        self.assertEqual(len(result.clauses), 1)
        self.assertEqual(result.clauses[0].risk_level, "high")

    @patch("app.services.clova_studio_service.httpx.Client")
    def test_auth_error_is_not_retryable(self, client_class: MagicMock) -> None:
        client_class.return_value.__enter__.return_value.post.return_value = _mock_response(
            401,
            {"status": {"code": "40100", "message": "Unauthorized"}},
        )

        with self.assertRaises(ClovaStudioError) as context:
            analyze_contract(
                "계약서",
                request_id="req-test",
                settings=TestSettings(),
            )

        self.assertFalse(context.exception.retryable)
        self.assertEqual(context.exception.status_code, 401)

    @patch("app.services.clova_studio_service.httpx.Client")
    def test_rate_limit_is_retryable(self, client_class: MagicMock) -> None:
        client_class.return_value.__enter__.return_value.post.return_value = _mock_response(
            429,
            {"status": {"code": "42900", "message": "Too Many Requests"}},
        )

        with self.assertRaises(ClovaStudioError) as context:
            analyze_contract(
                "계약서",
                request_id="req-test",
                settings=TestSettings(),
            )

        self.assertTrue(context.exception.retryable)
        self.assertEqual(context.exception.status_code, 429)

    def test_missing_api_key_is_not_retryable(self) -> None:
        settings = TestSettings()
        settings.clova_studio_api_key = None

        with self.assertRaises(ClovaStudioError) as context:
            analyze_contract(
                "계약서",
                request_id="req-test",
                settings=settings,
            )

        self.assertFalse(context.exception.retryable)


if __name__ == "__main__":
    unittest.main()
