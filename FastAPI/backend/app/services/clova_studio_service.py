from typing import Optional
import json

import httpx
from pydantic import BaseModel, ValidationError

from app.config import Settings, get_settings
from app.schemas.analysis_schema import ClauseAnalysis


class ClovaStudioError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        retryable: bool,
        status_code: Optional[int] = None,
    ) -> None:
        super().__init__(message)
        self.retryable = retryable
        self.status_code = status_code


class ClovaAnalysisPayload(BaseModel):
    clauses: list[ClauseAnalysis]


def _response_schema() -> dict[str, object]:
    return {
        "type": "object",
        "properties": {
            "clauses": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "clause_title": {
                            "type": "string",
                            "description": "Short title identifying the risky clause.",
                        },
                        "risk_level": {
                            "type": "string",
                            "enum": ["critical", "high", "medium", "low", "info"],
                        },
                        "summary": {
                            "type": "string",
                            "description": "Why the clause may create risk for the tenant.",
                        },
                        "legal_basis": {
                            "type": "string",
                            "description": "Relevant legal review point, not a definitive legal opinion.",
                        },
                        "diff_excerpt": {
                            "type": "string",
                            "description": "Exact short excerpt found in the supplied contract text.",
                        },
                    },
                    "required": [
                        "clause_title",
                        "risk_level",
                        "summary",
                        "legal_basis",
                        "diff_excerpt",
                    ],
                },
            }
        },
        "required": ["clauses"],
    }


def _build_request_payload(
    contract_text: str,
    *,
    include_legal_basis: bool,
    settings: Settings,
) -> dict[str, object]:
    legal_basis_instruction = (
        "각 항목에 관련 법률 검토 포인트를 간단히 포함하세요."
        if include_legal_basis
        else "legal_basis는 빈 문자열로 반환하세요."
    )
    sanitized_text = contract_text[: settings.clova_studio_max_input_chars]
    return {
        "messages": [
            {
                "role": "system",
                "content": (
                    "당신은 대한민국 주택 임대차 계약서의 위험 조항을 선별하는 보조 분석기입니다. "
                    "법률 자문이나 확정 판단을 하지 마세요. 제공된 계약서 텍스트에 실제로 존재하는 "
                    "문구만 분석하고, diff_excerpt는 반드시 원문에서 짧게 그대로 인용하세요. "
                    "근거가 부족하면 clauses를 빈 배열로 반환하세요. "
                    f"{legal_basis_instruction}"
                ),
            },
            {
                "role": "user",
                "content": f"개인정보가 마스킹된 계약서 텍스트:\n\n{sanitized_text}",
            },
        ],
        "topP": 0.8,
        "topK": 0,
        "maxCompletionTokens": 1800,
        "temperature": 0.1,
        "repetitionPenalty": 1.1,
        "thinking": {"effort": "none"},
        "stop": [],
        "responseFormat": {
            "type": "json",
            "schema": _response_schema(),
        },
    }


def _parse_response(response: httpx.Response) -> ClovaAnalysisPayload:
    try:
        response_body = response.json()
        content = response_body["result"]["message"]["content"]
        parsed_content = json.loads(content)
        return ClovaAnalysisPayload.model_validate(parsed_content)
    except (ValueError, KeyError, TypeError, ValidationError) as exc:
        raise ClovaStudioError(
            "CLOVA Studio returned an invalid structured response.",
            retryable=True,
            status_code=response.status_code,
        ) from exc


def analyze_contract(
    contract_text: str,
    *,
    request_id: str,
    include_legal_basis: bool = True,
    settings: Optional[Settings] = None,
) -> ClovaAnalysisPayload:
    active_settings = settings or get_settings()
    if not active_settings.clova_studio_api_key:
        raise ClovaStudioError(
            "CLOVA_STUDIO_API_KEY is not configured.",
            retryable=False,
        )

    redacted_contract_text = contract_text.strip()
    if not redacted_contract_text:
        redacted_contract_text = """
전세계약서 특약사항:
1. 임차인은 퇴거 시 모든 수리비와 원상복구 비용을 부담한다.
2. 임대인은 개인 사정에 따라 보증금 반환일을 조정할 수 있다.
3. 임차인은 계약 기간 중 발생하는 모든 하자에 대해 책임진다.
4. 임대인은 계약 종료 후 새로운 임차인이 구해진 뒤 보증금을 반환한다.
"""
    
    endpoint = (
        f"{active_settings.clova_studio_base_url}/v3/chat-completions/"
        f"{active_settings.clova_studio_model}"
    )
    headers = {
        "Authorization": f"Bearer {active_settings.clova_studio_api_key}",
        "X-NCP-CLOVASTUDIO-REQUEST-ID": request_id,
        "Content-Type": "application/json",
    }
    payload = _build_request_payload(
        contract_text,
        include_legal_basis=include_legal_basis,
        settings=active_settings,
    )

    try:
        with httpx.Client(timeout=active_settings.analysis_timeout_seconds) as client:
            response = client.post(endpoint, headers=headers, json=payload)
    except (httpx.TimeoutException, httpx.TransportError) as exc:
        raise ClovaStudioError(
            "CLOVA Studio request failed before receiving a response.",
            retryable=True,
        ) from exc

    if response.status_code >= 400:
        retryable = response.status_code == 429 or response.status_code >= 500
        raise ClovaStudioError(
            f"CLOVA Studio request failed with HTTP {response.status_code}.",
            retryable=retryable,
            status_code=response.status_code,
        )

    return _parse_response(response)
