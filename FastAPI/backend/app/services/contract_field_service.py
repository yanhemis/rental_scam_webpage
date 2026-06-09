from __future__ import annotations

import re
from dataclasses import dataclass

from app.schemas.document_schema import (
    ContractDocumentType,
    ContractFieldEvidence,
    ContractFieldExtractionResult,
    ContractFieldProfile,
    ContractFieldValue,
)
from app.schemas.extraction_schema import ExtractedTextLocation


@dataclass(frozen=True)
class ContractProfileSpec:
    label: str
    required_fields: tuple[str, ...]
    likely_fields: tuple[str, ...]


PROFILE_SPECS: dict[ContractDocumentType, ContractProfileSpec] = {
    ContractDocumentType.jeonse: ContractProfileSpec(
        label="전세",
        required_fields=(
            "contract_type",
            "deposit_amount",
            "lease_start_date",
            "lease_end_date",
            "landlord_name",
            "tenant_name",
            "address",
        ),
        likely_fields=(
            "confirmed_date_status",
            "move_in_report_status",
            "priority_rights",
            "special_terms",
            "risk_flags",
        ),
    ),
    ContractDocumentType.monthly_rent: ContractProfileSpec(
        label="월세",
        required_fields=(
            "contract_type",
            "deposit_amount",
            "monthly_rent",
            "lease_start_date",
            "lease_end_date",
            "landlord_name",
            "tenant_name",
            "address",
        ),
        likely_fields=(
            "maintenance_fee",
            "payment_due_day",
            "confirmed_date_status",
            "move_in_report_status",
            "special_terms",
            "risk_flags",
        ),
    ),
    ContractDocumentType.mixed_rent: ContractProfileSpec(
        label="반전세",
        required_fields=(
            "contract_type",
            "deposit_amount",
            "monthly_rent",
            "lease_start_date",
            "lease_end_date",
            "landlord_name",
            "tenant_name",
            "address",
        ),
        likely_fields=(
            "maintenance_fee",
            "payment_due_day",
            "confirmed_date_status",
            "move_in_report_status",
            "priority_rights",
            "special_terms",
            "risk_flags",
        ),
    ),
    ContractDocumentType.sale: ContractProfileSpec(
        label="매매",
        required_fields=(
            "contract_type",
            "sale_price",
            "seller_name",
            "buyer_name",
            "address",
            "contract_payment",
            "balance_payment",
            "ownership_transfer_date",
        ),
        likely_fields=(
            "intermediate_payment",
            "mortgage_status",
            "registration_status",
            "special_terms",
            "risk_flags",
        ),
    ),
    ContractDocumentType.unknown: ContractProfileSpec(
        label="모름",
        required_fields=("contract_type", "address"),
        likely_fields=("deposit_amount", "monthly_rent", "special_terms", "risk_flags"),
    ),
}

FIELD_LABELS: dict[str, str] = {
    "contract_type": "계약 유형",
    "deposit_amount": "보증금",
    "monthly_rent": "월세",
    "lease_start_date": "임대차 시작일",
    "lease_end_date": "임대차 종료일",
    "landlord_name": "임대인",
    "tenant_name": "임차인",
    "address": "주소",
    "confirmed_date_status": "확정일자",
    "move_in_report_status": "전입신고",
    "priority_rights": "선순위 권리",
    "special_terms": "특약",
    "risk_flags": "위험 신호",
    "maintenance_fee": "관리비",
    "payment_due_day": "납부일",
    "sale_price": "매매대금",
    "seller_name": "매도인",
    "buyer_name": "매수인",
    "contract_payment": "계약금",
    "intermediate_payment": "중도금",
    "balance_payment": "잔금",
    "ownership_transfer_date": "소유권 이전일",
    "mortgage_status": "근저당",
    "registration_status": "등기 상태",
}

NAME_STOPWORDS = (
    "또는",
    "불이행",
    "손해배상",
    "계약상",
    "상대방",
    "해지",
    "종료",
    "동의",
    "임차권",
    "임대차",
)

KOREAN_DIGITS = {
    "영": 0,
    "공": 0,
    "일": 1,
    "한": 1,
    "이": 2,
    "둘": 2,
    "삼": 3,
    "사": 4,
    "오": 5,
    "육": 6,
    "륙": 6,
    "칠": 7,
    "팔": 8,
    "구": 9,
}

SMALL_UNITS = {"십": 10, "백": 100, "천": 1000}
LARGE_UNITS = {"만": 10_000, "억": 100_000_000}


def extract_contract_fields(
    text: str,
    locations: list[ExtractedTextLocation],
    document_type: ContractDocumentType | None = None,
) -> ContractFieldExtractionResult:
    requested_type = document_type or ContractDocumentType.unknown
    selected_type = requested_type
    if selected_type == ContractDocumentType.unknown:
        selected_type = _detect_document_type(text)

    profile_spec = PROFILE_SPECS[selected_type]
    profile = ContractFieldProfile(
        document_type=selected_type,
        label=profile_spec.label,
        required_fields=list(profile_spec.required_fields),
        likely_fields=list(profile_spec.likely_fields),
    )

    fields: dict[str, ContractFieldValue] = {}
    fields["contract_type"] = _contract_type_field(selected_type, text, locations)

    if selected_type in {
        ContractDocumentType.jeonse,
        ContractDocumentType.monthly_rent,
        ContractDocumentType.mixed_rent,
        ContractDocumentType.unknown,
    }:
        fields["deposit_amount"] = _amount_field(
            text,
            locations,
            "deposit_amount",
            ("보증금", "임대보증금"),
        )
        fields["monthly_rent"] = _amount_field(
            text,
            locations,
            "monthly_rent",
            ("월세", "차임", "월 차임", "월차임"),
        )
        start_date, end_date = _lease_period_fields(text, locations)
        fields["lease_start_date"] = start_date
        fields["lease_end_date"] = end_date
        fields["landlord_name"] = _party_name_field(text, locations, "landlord_name", ("임대인",))
        fields["tenant_name"] = _party_name_field(text, locations, "tenant_name", ("임차인",))

    if selected_type == ContractDocumentType.sale:
        fields["sale_price"] = _amount_field(text, locations, "sale_price", ("매매대금", "매매 대금"))
        fields["contract_payment"] = _amount_field(text, locations, "contract_payment", ("계약금",))
        fields["intermediate_payment"] = _amount_field(text, locations, "intermediate_payment", ("중도금",))
        fields["balance_payment"] = _amount_field(text, locations, "balance_payment", ("잔금",))
        fields["ownership_transfer_date"] = _single_date_field(
            text,
            locations,
            "ownership_transfer_date",
            ("소유권이전", "이전등기", "소유권 이전"),
        )
        fields["seller_name"] = _party_name_field(text, locations, "seller_name", ("매도인",))
        fields["buyer_name"] = _party_name_field(text, locations, "buyer_name", ("매수인",))

    fields["address"] = _address_field(text, locations)
    fields["confirmed_date_status"] = _status_field(text, locations, "confirmed_date_status", ("확정일자",))
    fields["move_in_report_status"] = _status_field(text, locations, "move_in_report_status", ("전입신고", "주민등록"))
    fields["priority_rights"] = _status_field(text, locations, "priority_rights", ("선순위", "근저당", "가압류", "압류"))
    fields["special_terms"] = _special_terms_field(text, locations)
    fields["risk_flags"] = _risk_flags_field(text, locations)

    required = {field_id: fields.get(field_id, _missing_field(field_id)) for field_id in profile.required_fields}
    likely = {field_id: fields.get(field_id, _missing_field(field_id)) for field_id in profile.likely_fields}
    other = {
        field_id: value
        for field_id, value in fields.items()
        if field_id not in required and field_id not in likely
    }
    missing_fields = [
        field_id
        for field_id, value in required.items()
        if value.value in (None, "")
    ]
    low_confidence_fields = [
        field_id
        for field_id, value in fields.items()
        if value.value not in (None, "") and value.confidence < 0.7
    ]

    return ContractFieldExtractionResult(
        profile=profile,
        fields=fields,
        field_groups={"required": required, "likely": likely, "other": other},
        missing_fields=missing_fields,
        low_confidence_fields=low_confidence_fields,
        needs_review=bool(missing_fields or low_confidence_fields),
    )


def _detect_document_type(text: str) -> ContractDocumentType:
    head = _compact(text[:1500])
    if "매매" in head or "매도인" in head or "매수인" in head:
        return ContractDocumentType.sale
    has_deposit = "보증금" in head
    has_monthly = "월세" in head or "차임" in head
    if has_deposit and has_monthly:
        return ContractDocumentType.mixed_rent
    if "전세" in head or has_deposit:
        return ContractDocumentType.jeonse
    if has_monthly:
        return ContractDocumentType.monthly_rent
    return ContractDocumentType.unknown


def _contract_type_field(
    document_type: ContractDocumentType,
    text: str,
    locations: list[ExtractedTextLocation],
) -> ContractFieldValue:
    if document_type != ContractDocumentType.unknown:
        label = PROFILE_SPECS[document_type].label
        return _field(label, label, 0.95, False, _evidence(locations, ("전세", "월세", "매매", label), label))
    detected_type = _detect_document_type(text)
    if detected_type == ContractDocumentType.unknown:
        return _missing_field("contract_type")
    label = PROFILE_SPECS[detected_type].label
    return _field(label, label, 0.65, True, _evidence(locations, ("전세", "월세", "매매", label), label))


def _amount_field(
    text: str,
    locations: list[ExtractedTextLocation],
    field_id: str,
    labels: tuple[str, ...],
) -> ContractFieldValue:
    search_text = _compact(text)
    label_pattern = "|".join(re.escape(_compact(label)) for label in labels)
    window_pattern = re.compile(rf"({label_pattern})(.{{0,90}})")
    for match in window_pattern.finditer(search_text):
        window = match.group(2)
        amount = _extract_amount_from_text(window)
        if amount is None:
            continue
        value_text = match.group(0)
        evidence = _evidence(locations, labels, value_text)
        confidence = 0.82 if evidence else 0.68
        return _field(amount, _format_won(amount), confidence, confidence < 0.75, evidence)
    return _missing_field(field_id)


def _lease_period_fields(
    text: str,
    locations: list[ExtractedTextLocation],
) -> tuple[ContractFieldValue, ContractFieldValue]:
    date_matches = list(_iter_dates(text))
    if len(date_matches) < 2:
        return _missing_field("lease_start_date"), _missing_field("lease_end_date")

    preferred = _find_date_pair_near_period_label(text, date_matches) or (date_matches[0], date_matches[1])
    start, end = preferred
    evidence = _evidence(locations, ("임대차기간", "존속기간", "기간", "부터", "까지"), f"{start[0]} {end[0]}")
    confidence = 0.78 if evidence else 0.62
    return (
        _field(start[1], start[1], confidence, confidence < 0.7, evidence),
        _field(end[1], end[1], confidence, confidence < 0.7, evidence),
    )


def _single_date_field(
    text: str,
    locations: list[ExtractedTextLocation],
    field_id: str,
    labels: tuple[str, ...],
) -> ContractFieldValue:
    compact_text = _compact(text)
    label_pattern = "|".join(re.escape(_compact(label)) for label in labels)
    for match in re.finditer(rf"({label_pattern})(.{{0,80}})", compact_text):
        dates = list(_iter_dates(match.group(2)))
        if dates:
            evidence = _evidence(locations, labels, dates[0][0])
            return _field(dates[0][1], dates[0][1], 0.74, not evidence, evidence)
    return _missing_field(field_id)


def _party_name_field(
    text: str,
    locations: list[ExtractedTextLocation],
    field_id: str,
    labels: tuple[str, ...],
) -> ContractFieldValue:
    follower_labels = ("임대인", "임차인", "매도인", "매수인", "주소", "소재지", "계약", "특약")
    for label in labels:
        pattern = re.compile(
            rf"{re.escape(label)}\s*[:：]?\s*([가-힣]{{2,4}})(?=\s*(?:{'|'.join(follower_labels)}|$))"
        )
        match = pattern.search(text)
        if match:
            name = match.group(1)
            evidence = _evidence(locations, labels, name)
            confidence = 0.72 if evidence else 0.58
            return _field(name, name, confidence, True, evidence)

    compact_text = _compact(text)
    label_pattern = "|".join(re.escape(_compact(label)) for label in labels)
    follower_pattern = "|".join(re.escape(_compact(label)) for label in follower_labels)
    for match in re.finditer(rf"({label_pattern})([가-힣]{{2,4}})(?=({follower_pattern})|$)", compact_text):
        window = match.group(2)
        if any(stopword in window for stopword in NAME_STOPWORDS):
            continue
        name = window
        if name in labels or name in NAME_STOPWORDS:
            continue
        evidence = _evidence(locations, labels, name)
        confidence = 0.72 if evidence else 0.55
        return _field(name, name, confidence, True, evidence)
    return _missing_field(field_id)


def _address_field(text: str, locations: list[ExtractedTextLocation]) -> ContractFieldValue:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    label_terms = ("소재지", "주소", "부동산의표시", "부동산의 표시")
    for line in lines:
        compact_line = _compact(line)
        if "사무소" in compact_line or "중개사무소" in compact_line:
            continue
        if not any(_compact(label) in compact_line for label in label_terms):
            continue
        if not re.search(r"[가-힣]{2,}(시|군|구|동|로|길)", compact_line):
            continue
        address_match = re.search(r"(?:소재지|주소)\s*[:：]?\s*(.{4,80})", line)
        value = address_match.group(1).strip() if address_match else line[:80]
        evidence = _evidence(locations, label_terms, line)
        confidence = 0.7 if evidence else 0.55
        return _field(value, value, confidence, confidence < 0.75, evidence)
    return _missing_field("address")


def _status_field(
    text: str,
    locations: list[ExtractedTextLocation],
    field_id: str,
    labels: tuple[str, ...],
) -> ContractFieldValue:
    compact_text = _compact(text)
    if not any(_compact(label) in compact_text for label in labels):
        return _field(None, "예정", 0.45, True, [])
    positive_terms = ("완료", "접수", "신청", "가능", "없음")
    value = "확인 필요"
    confidence = 0.58
    for term in positive_terms:
        if term in compact_text:
            value = term
            confidence = 0.66
            break
    return _field(value, value, confidence, True, _evidence(locations, labels, value))


def _special_terms_field(text: str, locations: list[ExtractedTextLocation]) -> ContractFieldValue:
    compact_text = _compact(text)
    if "특약" not in compact_text:
        return _field(None, "확인 필요", 0.35, True, [])
    evidence = _evidence(locations, ("특약", "특약사항"), "특약")
    return _field("특약 조항 확인", "확인 필요", 0.62, True, evidence)


def _risk_flags_field(text: str, locations: list[ExtractedTextLocation]) -> ContractFieldValue:
    terms = ("반환 지연", "수선비", "원상복구", "근저당", "압류", "가압류", "위반건축물")
    hits = [term for term in terms if term.replace(" ", "") in _compact(text)]
    if not hits:
        return _field([], "없음", 0.5, True, [])
    return _field(hits, ", ".join(hits), 0.7, True, _evidence(locations, tuple(hits), " ".join(hits)))


def _extract_amount_from_text(text: str) -> int | None:
    number_match = re.search(r"([0-9][0-9,]{3,})", text)
    if number_match:
        return int(re.sub(r"\D", "", number_match.group(1)))

    korean_match = re.search(r"([일이삼사오육륙칠팔구십백천만억한공영\s]+)원?", text)
    if korean_match:
        return _parse_korean_amount(korean_match.group(1))
    return None


def _parse_korean_amount(value: str) -> int | None:
    compact_value = re.sub(r"\s|원|정|금", "", value)
    if not compact_value:
        return None

    total = 0
    section = 0
    number = 0
    found = False
    for char in compact_value:
        if char in KOREAN_DIGITS:
            number = KOREAN_DIGITS[char]
            found = True
            continue
        if char in SMALL_UNITS:
            section += (number or 1) * SMALL_UNITS[char]
            number = 0
            found = True
            continue
        if char in LARGE_UNITS:
            section += number
            total += (section or 1) * LARGE_UNITS[char]
            section = 0
            number = 0
            found = True
    amount = total + section + number
    return amount if found and amount > 0 else None


def _iter_dates(text: str):
    pattern = re.compile(r"(\d{4})\s*[년./-]\s*(\d{1,2})\s*[월./-]\s*(\d{1,2})")
    for match in pattern.finditer(text):
        year, month, day = match.groups()
        yield match.group(0), f"{year}.{int(month):02d}.{int(day):02d}", match.start()


def _find_date_pair_near_period_label(text: str, date_matches: list[tuple[str, str, int]]):
    label_positions = [match.start() for match in re.finditer(r"임대차\s*기간|존속\s*기간|기간|부터|까지", text)]
    if not label_positions:
        return None
    best_pair = None
    best_distance = 10**9
    for index in range(len(date_matches) - 1):
        pair = (date_matches[index], date_matches[index + 1])
        pair_pos = min(pair[0][2], pair[1][2])
        distance = min(abs(pair_pos - label_pos) for label_pos in label_positions)
        if distance < best_distance:
            best_pair = pair
            best_distance = distance
    return best_pair


def _evidence(
    locations: list[ExtractedTextLocation],
    label_terms: tuple[str, ...],
    value_text: str | int | float | bool | list | None,
) -> list[ContractFieldEvidence]:
    if not locations:
        return []

    label_terms_compact = tuple(_compact(str(term)) for term in label_terms if str(term).strip())
    value_compact = _compact(str(value_text or ""))
    value_fragments = [value_compact[:8], re.sub(r"\D", "", value_compact)[:8]]
    value_fragments = [fragment for fragment in value_fragments if len(fragment) >= 2]

    for index, location in enumerate(locations):
        token = _compact(location.text)
        label_hit = any(term and term in token for term in label_terms_compact)
        value_hit = any(fragment and fragment in token for fragment in value_fragments)
        if not label_hit and not value_hit:
            continue

        page_number = location.page_number
        window = [
            item
            for item in locations[max(0, index - 1) : index + 5]
            if item.page_number == page_number
        ]
        if not window:
            window = [location]
        label_items = [
            item
            for item in window
            if any(term and term in _compact(item.text) for term in label_terms_compact)
        ]
        value_items = [
            item
            for item in window
            if any(fragment and fragment in _compact(item.text) for fragment in value_fragments)
        ]
        ocr_values = [item.confidence for item in window if item.confidence is not None]
        return [
            ContractFieldEvidence(
                page_number=page_number,
                bbox=_union_bbox(window),
                coordinate_system=window[0].coordinate_system,
                span_ids=[item.span_id for item in window],
                text=" ".join(item.text for item in window),
                label_text=next((item.text for item in label_items), None),
                value_text=next((item.text for item in value_items), str(value_text or "") or None),
                label_bbox=_union_bbox(label_items) if label_items else None,
                value_bbox=_union_bbox(value_items) if value_items else None,
                match_confidence=0.75 if label_hit and value_hit else 0.6,
                ocr_confidence=sum(ocr_values) / len(ocr_values) if ocr_values else None,
            )
        ]
    return []


def _union_bbox(items: list[ExtractedTextLocation]) -> list[float]:
    if not items:
        return []
    return [
        min(item.bbox[0] for item in items),
        min(item.bbox[1] for item in items),
        max(item.bbox[2] for item in items),
        max(item.bbox[3] for item in items),
    ]


def _field(
    value: str | int | float | bool | list | None,
    display_value: str,
    confidence: float,
    needs_review: bool,
    evidence: list[ContractFieldEvidence],
) -> ContractFieldValue:
    return ContractFieldValue(
        value=value,
        display_value=display_value,
        confidence=round(confidence, 3),
        needs_review=needs_review,
        evidence=evidence,
    )


def _missing_field(field_id: str) -> ContractFieldValue:
    return ContractFieldValue(
        value=None,
        display_value="확인 필요",
        confidence=0.0,
        needs_review=True,
        evidence=[],
    )


def _format_won(value: int) -> str:
    return f"{value:,}원"


def _compact(value: str) -> str:
    return re.sub(r"\s+", "", str(value or ""))
