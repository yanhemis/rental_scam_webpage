import re
from datetime import date

from app.schemas.contract_extract_schema import ExtractedContractInfo


EXTRACTABLE_FIELDS = [
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
    "special_terms",
]

_DATE_PATTERN = re.compile(
    r"(?P<year>(?:19|20)\d{2})\s*(?:[.\-/년]\s*)?"
    r"(?P<month>\d{1,2})\s*(?:[.\-/월]\s*)?"
    r"(?P<day>\d{1,2})\s*(?:일)?"
)
_DATE_EXPR = (
    r"(?:19|20)\d{2}\s*(?:[.\-/년]\s*)?"
    r"\d{1,2}\s*(?:[.\-/월]\s*)?\d{1,2}\s*(?:일)?"
)
_KOREAN_DIGITS = {
    "영": 0,
    "공": 0,
    "일": 1,
    "이": 2,
    "삼": 3,
    "사": 4,
    "오": 5,
    "육": 6,
    "륙": 6,
    "칠": 7,
    "팔": 8,
    "구": 9,
}
_SMALL_AMOUNT_UNITS = {"십": 10, "백": 100, "천": 1000}
_BIG_AMOUNT_UNITS = [("조", 1_000_000_000_000), ("억", 100_000_000), ("만", 10_000)]
_STATUS_KEYWORDS = {
    "완료": ("완료", "완료됨", "신고완료", "받음", "받았", "있음"),
    "예정": ("예정", "예정일", "추후", "예정됨"),
    "없음": ("없음", "무", "해당없음", "미신고", "미부여", "없다"),
    "미정": ("미정", "불명", "확인필요", "확인 필요"),
}
_PARTY_BOUNDARY_LABELS = (
    "임대인",
    "집주인",
    "임차인",
    "세입자",
    "주민등록번호",
    "주소",
    "연락처",
    "서명",
)


def normalize_ocr_text(text: str) -> str:
    normalized = text or ""
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = normalized.replace("：", ":").replace("ㆍ", ".")
    normalized = normalized.replace("~", " ~ ").replace("〜", " ~ ")
    normalized = re.sub(r"[ \t\f\v]+", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    normalized = re.sub(r" *\n *", "\n", normalized)
    normalized = re.sub(r"(?<=\d)\s*,\s*(?=\d{3}\b)", ",", normalized)
    normalized = re.sub(
        r"((?:19|20)\d{2})\s*[./]\s*(\d{1,2})\s*[./]\s*(\d{1,2})",
        lambda match: _format_date_parts(match.group(1), match.group(2), match.group(3))
        or match.group(0),
        normalized,
    )
    return normalized.strip()


def extract_contract_type(text: str) -> tuple[str | None, float]:
    compact = re.sub(r"\s+", "", text)
    if "전세계약서" in compact or "전세권" in compact or "전세금" in compact:
        return "전세", 0.95
    if "전세" in compact and "월세" not in compact:
        return "전세", 0.88
    if "월세계약서" in compact or "월세" in compact or "차임" in compact:
        return "월세", 0.9
    if "주택임대차계약서" in compact or "임대차계약서" in compact:
        return "주택임대차", 0.82
    if "매매계약서" in compact:
        return "매매", 0.8
    return None, 0.0


def extract_deposit_amount(text: str) -> tuple[int | None, float]:
    deposit_keywords = ("보증금", "전세금", "전세보증금", "임대보증금", "보증 금액")
    lines = text.splitlines() or [text]

    for line in lines:
        if any(keyword in line for keyword in deposit_keywords):
            amount = _extract_amount_from_context(line)
            if amount is not None:
                return amount, 0.95

    keyword_pattern = "|".join(re.escape(keyword) for keyword in deposit_keywords)
    for match in re.finditer(keyword_pattern, text):
        context = text[match.end() : match.end() + 100]
        amount = _extract_amount_from_context(context)
        if amount is not None:
            return amount, 0.9

    amount = _extract_amount_from_context(text)
    if amount is not None:
        return amount, 0.65
    return None, 0.0


def extract_lease_period(text: str) -> tuple[str | None, str | None, float]:
    period_keywords = ("계약기간", "임대차기간", "임대 기간", "존속기간", "임대차 기간")
    period_pattern = re.compile(
        rf"(?:{'|'.join(period_keywords)})[^\n]{{0,100}}?"
        rf"(?P<start>{_DATE_EXPR})[^\n]{{0,40}}?"
        rf"(?:부터|에서|~|-|까지|至)[^\n]{{0,40}}?"
        rf"(?P<end>{_DATE_EXPR})"
    )
    match = period_pattern.search(text)
    if match:
        start_date = _normalize_date_match(match.group("start"))
        end_date = _normalize_date_match(match.group("end"))
        if start_date and end_date:
            return start_date, end_date, 0.95

    for line in text.splitlines():
        if any(keyword in line for keyword in period_keywords):
            dates = _extract_normalized_dates(line)
            if len(dates) >= 2:
                return dates[0], dates[1], 0.88

    dates = _extract_normalized_dates(text)
    if len(dates) >= 2:
        return dates[0], dates[1], 0.65
    return None, None, 0.0


def extract_confirmed_date_status(text: str) -> tuple[str | None, float]:
    return _extract_status_near_keywords(text, ("확정일자", "확정 일자"))


def extract_move_in_report_status(text: str) -> tuple[str | None, float]:
    return _extract_status_near_keywords(text, ("전입신고", "전입 신고", "입주신고"))


def extract_priority_rights(text: str) -> tuple[str | None, float]:
    right_terms = ("선순위", "근저당", "저당권", "가압류", "압류", "전세권", "담보권")
    contexts = [line for line in text.splitlines() if any(term in line for term in right_terms)]
    if not contexts:
        return None, 0.0

    context = " ".join(contexts)
    if re.search(r"(선순위.{0,12})?(없음|없다|무|말소|해지)", context):
        return "없음", 0.86

    found_terms = []
    for term in right_terms:
        if term in context and term not in found_terms:
            found_terms.append(term)
    if found_terms:
        return f"있음: {', '.join(found_terms)}", 0.78
    return "미정", 0.45


def extract_address(text: str) -> tuple[str | None, float]:
    address_keywords = ("소재지", "주소", "임대차 목적물", "목적물의 표시", "부동산의 표시")
    for line in text.splitlines():
        if any(keyword in line for keyword in address_keywords):
            cleaned = _clean_labeled_value(line, address_keywords)
            if len(cleaned) >= 6:
                return cleaned, 0.82

    address_pattern = re.compile(
        r"([가-힣]{2,}(?:특별시|광역시|도|시)\s+[^\n]{4,}"
        r"(?:로|길|동|읍|면|리)\s*\d*[^\n]*)"
    )
    match = address_pattern.search(text)
    if match:
        return _clean_value(match.group(1)), 0.65
    return None, 0.0


def extract_party_names(text: str) -> tuple[str | None, str | None, float]:
    landlord = _extract_party_name(text, ("임대인", "집주인"))
    tenant = _extract_party_name(text, ("임차인", "세입자"))
    confidence = 0.0
    if landlord and tenant:
        confidence = 0.86
    elif landlord or tenant:
        confidence = 0.62
    return landlord, tenant, confidence


def extract_special_terms(text: str) -> tuple[list[str], float]:
    lines = text.splitlines()
    terms: list[str] = []
    collecting = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if collecting and terms:
                break
            continue

        if "특약" in stripped:
            collecting = True
            inline_value = _clean_labeled_value(stripped, ("특약사항", "특약"))
            if inline_value and "특약" not in inline_value:
                terms.append(_clean_special_term(inline_value))
            continue

        if collecting:
            if re.search(r"^(임대인|임차인|중개업자|공인중개사|서명|날인|계약내용)", stripped):
                break
            terms.append(_clean_special_term(stripped))
            if len(terms) >= 10:
                break

    terms = [term for term in terms if term]
    if terms:
        return terms, 0.82
    return [], 0.0


def extract_contract_fields(
    text: str,
    document_id: str | None = None,
) -> ExtractedContractInfo:
    normalized_text = normalize_ocr_text(text)
    contract_type, contract_type_confidence = extract_contract_type(normalized_text)
    deposit_amount, deposit_confidence = extract_deposit_amount(normalized_text)
    lease_start_date, lease_end_date, lease_confidence = extract_lease_period(normalized_text)
    confirmed_status, confirmed_confidence = extract_confirmed_date_status(normalized_text)
    move_in_status, move_in_confidence = extract_move_in_report_status(normalized_text)
    priority_rights, priority_confidence = extract_priority_rights(normalized_text)
    address, address_confidence = extract_address(normalized_text)
    landlord_name, tenant_name, party_confidence = extract_party_names(normalized_text)
    special_terms, special_terms_confidence = extract_special_terms(normalized_text)

    field_confidence = {
        "contract_type": _clamp_confidence(contract_type_confidence),
        "deposit_amount": _clamp_confidence(deposit_confidence),
        "lease_start_date": _clamp_confidence(lease_confidence if lease_start_date else 0.0),
        "lease_end_date": _clamp_confidence(lease_confidence if lease_end_date else 0.0),
        "confirmed_date_status": _clamp_confidence(confirmed_confidence),
        "move_in_report_status": _clamp_confidence(move_in_confidence),
        "priority_rights": _clamp_confidence(priority_confidence),
        "address": _clamp_confidence(address_confidence),
        "landlord_name": _clamp_confidence(party_confidence if landlord_name else 0.0),
        "tenant_name": _clamp_confidence(party_confidence if tenant_name else 0.0),
        "special_terms": _clamp_confidence(special_terms_confidence),
    }

    result = ExtractedContractInfo(
        document_id=document_id,
        contract_type=contract_type,
        deposit_amount=deposit_amount,
        lease_start_date=lease_start_date,
        lease_end_date=lease_end_date,
        confirmed_date_status=confirmed_status,
        move_in_report_status=move_in_status,
        priority_rights=priority_rights,
        address=address,
        landlord_name=landlord_name,
        tenant_name=tenant_name,
        special_terms=special_terms,
        field_confidence=field_confidence,
    )
    result.missing_fields = [
        field
        for field in EXTRACTABLE_FIELDS
        if (getattr(result, field) in (None, "") or getattr(result, field) == [])
    ]
    return result


def _format_date_parts(year: str, month: str, day: str) -> str | None:
    try:
        normalized = date(int(year), int(month), int(day))
    except ValueError:
        return None
    return normalized.isoformat()


def _normalize_date_match(value: str) -> str | None:
    match = _DATE_PATTERN.search(value)
    if match is None:
        return None
    return _format_date_parts(match.group("year"), match.group("month"), match.group("day"))


def _extract_normalized_dates(text: str) -> list[str]:
    dates = []
    for match in _DATE_PATTERN.finditer(text):
        normalized = _format_date_parts(
            match.group("year"),
            match.group("month"),
            match.group("day"),
        )
        if normalized and normalized not in dates:
            dates.append(normalized)
    return dates


def _extract_amount_from_context(context: str) -> int | None:
    amount_patterns = [
        r"(\d{1,3}(?:,\d{3})+|\d+)\s*원",
        r"([0-9일이삼사오육륙칠팔구십백천만억조\s]+억[0-9일이삼사오육륙칠팔구십백천만억조\s]*(?:만)?\s*원?)",
        r"([0-9일이삼사오육륙칠팔구십백천만억조\s]+만\s*원)",
        r"([일이삼사오육륙칠팔구십백천만억조\s]+원)",
    ]
    for pattern in amount_patterns:
        for match in re.finditer(pattern, context):
            amount = _parse_amount(match.group(1))
            if amount is not None and amount > 0:
                return amount
    return None


def _parse_amount(value: str) -> int | None:
    cleaned = (
        value.replace(",", "")
        .replace(" ", "")
        .replace("원정", "")
        .replace("원", "")
        .replace("일금", "")
        .replace("금", "")
    )
    cleaned = re.sub(r"[^0-9일이삼사오육륙칠팔구십백천만억조]", "", cleaned)
    if not cleaned:
        return None
    if cleaned.isdigit():
        return int(cleaned)

    total = 0
    remaining = cleaned
    matched_big_unit = False
    for unit, multiplier in _BIG_AMOUNT_UNITS:
        if unit not in remaining:
            continue
        matched_big_unit = True
        segment, remaining = remaining.split(unit, 1)
        small_number = _parse_small_amount_number(segment)
        if small_number is None:
            return None
        total += small_number * multiplier

    if matched_big_unit:
        if remaining:
            remainder = _parse_small_amount_number(remaining)
            if remainder is not None:
                total += remainder
        return total

    return _parse_small_amount_number(cleaned)


def _parse_small_amount_number(value: str) -> int | None:
    if value == "":
        return 1
    if value.isdigit():
        return int(value)

    total = 0
    current = 0
    number_buffer = ""

    for char in value:
        if char.isdigit():
            number_buffer += char
            current = int(number_buffer)
            continue
        number_buffer = ""

        if char in _KOREAN_DIGITS:
            current = _KOREAN_DIGITS[char]
            continue
        if char in _SMALL_AMOUNT_UNITS:
            if current == 0:
                current = 1
            total += current * _SMALL_AMOUNT_UNITS[char]
            current = 0
            continue
        return None

    return total + current


def _extract_status_near_keywords(text: str, keywords: tuple[str, ...]) -> tuple[str | None, float]:
    for line in text.splitlines():
        if any(keyword in line for keyword in keywords):
            status = _detect_status_value(line)
            if status:
                return status, 0.84
            return "미정", 0.42
    for keyword in keywords:
        index = text.find(keyword)
        if index == -1:
            continue
        context = text[max(0, index - 20) : index + 60]
        status = _detect_status_value(context)
        if status:
            return status, 0.72
    return None, 0.0


def _detect_status_value(context: str) -> str | None:
    compact = re.sub(r"\s+", "", context)
    for status, keywords in _STATUS_KEYWORDS.items():
        if any(keyword in compact for keyword in keywords):
            return status
    return None


def _extract_party_name(text: str, keywords: tuple[str, ...]) -> str | None:
    for line in text.splitlines():
        matched_keyword = next((keyword for keyword in keywords if keyword in line), None)
        if matched_keyword is None:
            continue

        cleaned = line.split(matched_keyword, 1)[1]
        boundary_labels = [
            label
            for label in _PARTY_BOUNDARY_LABELS
            if label not in keywords and label in cleaned
        ]
        if boundary_labels:
            boundary_index = min(cleaned.index(label) for label in boundary_labels)
            cleaned = cleaned[:boundary_index]
        cleaned = re.sub(r"(성명|이름|성함|명칭|주민등록번호|주소|연락처)", " ", cleaned)
        cleaned = _clean_value(cleaned)
        match = re.search(r"([가-힣]{2,8}|[A-Za-z][A-Za-z\s]{1,30})", cleaned)
        if match:
            return _clean_value(match.group(1))
    return None


def _clean_labeled_value(line: str, labels: tuple[str, ...]) -> str:
    cleaned = line
    for label in labels:
        cleaned = cleaned.replace(label, " ")
    cleaned = re.sub(r"^[\s:.\-()]+", "", cleaned)
    return _clean_value(cleaned)


def _clean_value(value: str) -> str:
    value = re.sub(r"\s+", " ", value or "")
    return value.strip(" :.-\t")


def _clean_special_term(value: str) -> str:
    value = re.sub(r"^\s*(?:[-*ㆍ]|\d+[.)])\s*", "", value)
    return _clean_value(value)


def _clamp_confidence(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 2)
