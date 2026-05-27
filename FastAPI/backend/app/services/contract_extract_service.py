import re
from datetime import datetime

from app.schemas.contract_extract_schema import ExtractedContractInfo

STATUS_KEYWORDS = {
    "완료": ["완료", "있음", "완료됨"],
    "예정": ["예정"],
    "없음": ["없음", "해당없음"],
    "미정": ["미정"],
}



def normalize_ocr_text(text: str) -> str:
    normalized = (text or "").replace("\r", "\n")
    normalized = re.sub(r"[\t\u00a0]", " ", normalized)
    normalized = re.sub(r"[ ]{2,}", " ", normalized)
    normalized = re.sub(r"\n{2,}", "\n", normalized)
    return normalized.strip()


def _normalize_date(y: str, m: str, d: str) -> str | None:
    try:
        return datetime(int(y), int(m), int(d)).strftime("%Y-%m-%d")
    except ValueError:
        return None


def extract_contract_type(text: str) -> tuple[str | None, float]:
    if "전세" in text:
        return "전세", 0.98
    if "월세" in text:
        return "월세", 0.95
    if "임대차" in text:
        return "임대차", 0.8
    return None, 0.0


def _korean_to_number(value: str) -> int:
    small_units = {"천": 1_000, "백": 100, "십": 10}
    digit_units = {"일": 1, "이": 2, "삼": 3, "사": 4, "오": 5, "육": 6, "칠": 7, "팔": 8, "구": 9}

    total, section, current = 0, 0, 0
    compact = value.replace(" ", "")
    for ch in compact:
        if ch in digit_units:
            current = digit_units[ch]
        elif ch in small_units:
            section += (current or 1) * small_units[ch]
            current = 0
        elif ch == "억":
            section += current
            total += section * 100_000_000
            section, current = 0, 0
        elif ch == "만":
            section += current
            total += section * 10_000
            section, current = 0, 0
    return total + section + current


def extract_deposit_amount(text: str) -> tuple[int | None, float]:
    direct = re.search(r"보증금\s*[:：]?\s*([0-9][0-9,]*)\s*원", text)
    if direct:
        return int(direct.group(1).replace(",", "")), 0.97

    mixed = re.search(r"([0-9]+)\s*억\s*([0-9]+)\s*천\s*만\s*원", text)
    if mixed:
        eok = int(mixed.group(1)) * 100_000_000
        chunk = int(mixed.group(2)) * 10_000_000
        return eok + chunk, 0.9

    korean = re.search(r"([일이삼사오육칠팔구십백천억만\s]+)원", text)
    if korean and "보증금" in text[max(0, korean.start() - 20):korean.start() + 1]:
        value = _korean_to_number(korean.group(1))
        if value > 0:
            return value, 0.82

    return None, 0.0


def extract_lease_period(text: str) -> tuple[str | None, str | None, float]:
    patterns = [
        r"(\d{4})[.\-/년\s]+(\d{1,2})[.\-/월\s]+(\d{1,2})일?\s*[~〜\-]\s*(\d{4})[.\-/년\s]+(\d{1,2})[.\-/월\s]+(\d{1,2})일?",
        r"임대차\s*기간\s*[:：]?\s*(\d{4})[.\-/년\s]+(\d{1,2})[.\-/월\s]+(\d{1,2})일?\s*부터\s*(\d{4})[.\-/년\s]+(\d{1,2})[.\-/월\s]+(\d{1,2})일?",
    ]
    for pattern in patterns:
        m = re.search(pattern, text)
        if m:
            start = _normalize_date(m.group(1), m.group(2), m.group(3))
            end = _normalize_date(m.group(4), m.group(5), m.group(6))
            if start and end:
                return start, end, 0.93
    return None, None, 0.0


def _extract_status(text: str, anchor: str) -> tuple[str | None, float]:
    idx = text.find(anchor)
    if idx < 0:
        return None, 0.0
    window = text[idx: idx + 80]
    for status, keywords in STATUS_KEYWORDS.items():
        if any(keyword in window for keyword in keywords):
            return status, 0.85
    return None, 0.2


def extract_confirmed_date_status(text: str) -> tuple[str | None, float]:
    return _extract_status(text, "확정일자")


def extract_move_in_report_status(text: str) -> tuple[str | None, float]:
    return _extract_status(text, "전입신고")


def extract_priority_rights(text: str) -> tuple[str | None, float]:
    if "우선변제권" in text and "있" in text[text.find("우선변제권"): text.find("우선변제권") + 50]:
        return "완료", 0.8
    if "우선변제권" in text and "없" in text[text.find("우선변제권"): text.find("우선변제권") + 50]:
        return "없음", 0.8
    return None, 0.0


def extract_address(text: str) -> tuple[str | None, float]:
    m = re.search(r"((?:서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주)[^\n]{5,80})", text)
    return (m.group(1).strip(), 0.8) if m else (None, 0.0)


def extract_party_names(text: str) -> tuple[str | None, str | None, float]:
    landlord = None
    tenant = None
    m1 = re.search(r"임대인\s*[:：]?\s*([가-힣]{2,5})", text)
    m2 = re.search(r"임차인\s*[:：]?\s*([가-힣]{2,5})", text)
    if m1:
        landlord = m1.group(1)
    if m2:
        tenant = m2.group(1)
    confidence = 0.88 if landlord and tenant else (0.6 if landlord or tenant else 0.0)
    return landlord, tenant, confidence


def extract_special_terms(text: str) -> tuple[list[str], float]:
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    capture = [line for line in lines if "특약" in line or line.startswith("-") or line.startswith("*")]
    return capture[:10], (0.75 if capture else 0.0)


def extract_contract_fields(text: str, document_id: str | None = None) -> ExtractedContractInfo:
    normalized = normalize_ocr_text(text)
    contract_type, contract_type_cf = extract_contract_type(normalized)
    deposit_amount, deposit_cf = extract_deposit_amount(normalized)
    lease_start_date, lease_end_date, lease_cf = extract_lease_period(normalized)
    confirmed_date_status, confirmed_cf = extract_confirmed_date_status(normalized)
    move_in_report_status, move_cf = extract_move_in_report_status(normalized)
    priority_rights, priority_cf = extract_priority_rights(normalized)
    address, address_cf = extract_address(normalized)
    landlord_name, tenant_name, names_cf = extract_party_names(normalized)
    special_terms, special_cf = extract_special_terms(normalized)

    field_confidence = {
        "contract_type": contract_type_cf,
        "deposit_amount": deposit_cf,
        "lease_start_date": lease_cf,
        "lease_end_date": lease_cf,
        "confirmed_date_status": confirmed_cf,
        "move_in_report_status": move_cf,
        "priority_rights": priority_cf,
        "address": address_cf,
        "landlord_name": names_cf,
        "tenant_name": names_cf,
        "special_terms": special_cf,
    }

    result = ExtractedContractInfo(
        document_id=document_id,
        contract_type=contract_type,
        deposit_amount=deposit_amount,
        lease_start_date=lease_start_date,
        lease_end_date=lease_end_date,
        confirmed_date_status=confirmed_date_status,
        move_in_report_status=move_in_report_status,
        priority_rights=priority_rights,
        address=address,
        landlord_name=landlord_name,
        tenant_name=tenant_name,
        special_terms=special_terms,
        field_confidence=field_confidence,
    )

    required_fields = [
        "contract_type",
        "deposit_amount",
        "lease_start_date",
        "lease_end_date",
        "confirmed_date_status",
        "move_in_report_status",
        "priority_rights",
        "address",
        "landlord_name",
        "tenant_name",
    ]
    result.missing_fields = [field for field in required_fields if getattr(result, field) in (None, "")]
    return result
