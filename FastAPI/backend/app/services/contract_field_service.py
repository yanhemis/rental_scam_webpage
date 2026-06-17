from __future__ import annotations
from typing import Optional, Union

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
            "land_area",
            "building_info",
            "lease_area",
            "contract_payment",
            "balance_payment",
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
            "land_area",
            "building_info",
            "lease_area",
            "contract_payment",
            "balance_payment",
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
            "land_area",
            "building_info",
            "lease_area",
            "contract_payment",
            "balance_payment",
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
            "land_area",
            "building_info",
            "lease_area",
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
    "land_area": "토지",
    "building_info": "건물",
    "lease_area": "임대할 부분",
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
    document_type: Optional[ContractDocumentType] = None,
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
        fields["contract_payment"] = _missing_field("contract_payment")
        fields["intermediate_payment"] = _missing_field("intermediate_payment")
        fields["balance_payment"] = _missing_field("balance_payment")
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
    fields["land_area"] = _missing_field("land_area")
    fields["building_info"] = _missing_field("building_info")
    fields["lease_area"] = _missing_field("lease_area")
    fields["confirmed_date_status"] = _status_field(text, locations, "confirmed_date_status", ("확정일자",))
    fields["move_in_report_status"] = _status_field(text, locations, "move_in_report_status", ("전입신고", "주민등록"))
    fields["priority_rights"] = _status_field(text, locations, "priority_rights", ("선순위", "근저당", "가압류", "압류"))
    fields["special_terms"] = _special_terms_field(text, locations)
    fields["risk_flags"] = _risk_flags_field(text, locations)
    axis_candidates = _extract_axis_field_candidates(locations)
    fields.update(_merge_axis_candidates(fields, axis_candidates))
    _infer_missing_payment_fields(fields)
    _repair_lease_period_from_text(fields, text)
    _repair_property_fields_from_text(fields, text)
    if fields["special_terms"].value in (None, ""):
        fields["special_terms"] = _special_terms_from_risk_flags(fields["risk_flags"])

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
    compact_labels = sorted((re.escape(_compact(label)) for label in labels), key=len, reverse=True)
    label_pattern = "|".join(compact_labels)
    window_pattern = re.compile(rf"(?=({label_pattern})(.{{0,90}}))")
    candidates: list[tuple[int, int, str]] = []
    for match in window_pattern.finditer(search_text):
        label = match.group(1)
        window = match.group(2)
        if field_id == "monthly_rent" and label == "월세" and window.startswith(("계약", "계약서")):
            continue
        amount = _extract_amount_from_text(window)
        if amount is None:
            continue
        if not _amount_in_expected_range(field_id, amount):
            continue
        value_text = match.group(0)

        distance = _amount_distance_from_label(window)
        candidates.append((distance, amount, value_text))

    if candidates:
        _distance, amount, value_text = min(candidates, key=lambda item: item[0])
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
    if start[1] == end[1]:
        return _missing_field("lease_start_date"), _missing_field("lease_end_date")
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
            rf"{re.escape(label)}(?:\s+|[:：]\s*)([가-힣]{{2,4}})(?=\s*(?:{'|'.join(follower_labels)}|$))"
        )
        match = pattern.search(text)
        if match:
            name = match.group(1)
            if name in labels or name in NAME_STOPWORDS:
                continue
            evidence = _evidence(locations, labels, name)
            confidence = 0.72 if evidence else 0.58
            return _field(name, name, confidence, True, evidence)

    return _missing_field(field_id)


def _address_field(text: str, locations: list[ExtractedTextLocation]) -> ContractFieldValue:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    label_terms = ("소재지", "주소", "부동산의표시", "부동산의 표시")
    for index, line in enumerate(lines):
        compact_line = _compact(line)
        if "사무소" in compact_line or "중개사무소" in compact_line:
            continue
        if not any(_compact(label) in compact_line for label in label_terms):
            continue

        candidates = []
        address_match = re.search(r"(?:소\s*재\s*지|주\s*소)\s*[:：]?\s*(.{4,100})", line)
        if address_match:
            candidates.append(address_match.group(1).strip())
        candidates.append(_strip_property_suffix(line[:120]))
        if index + 1 < len(lines):
            candidates.append(_strip_property_suffix(lines[index + 1][:120]))

        for value in candidates:
            value = _clean_address_value(value)
            if not _looks_like_address(_compact(value)):
                continue
            evidence = _evidence(locations, label_terms, value) or _evidence(locations, label_terms, line)
            confidence = 0.76 if evidence else 0.62
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
    terms = (
        "반환 지연",
        "수선비",
        "원상복구",
        "근저당",
        "압류",
        "가압류",
        "위반건축물",
        "중개보수",
        "증개보수",
        "중개보스",
        "거래가액",
        "거라가먹",
        "거라 가먹",
    )
    hits = [term for term in terms if term.replace(" ", "") in _compact(text)]
    if any(term in _compact(text) for term in ("중개보수", "증개보수", "중개보스")):
        hits.append("중개보수 0.9% 확인")
    hits = list(dict.fromkeys(hits))
    if not hits:
        return _field([], "없음", 0.5, True, [])
    return _field(hits, ", ".join(hits), 0.7, True, _evidence(locations, tuple(hits), " ".join(hits)))


def _special_terms_from_risk_flags(risk_flags: ContractFieldValue) -> ContractFieldValue:
    if not risk_flags.evidence:
        return _missing_field("special_terms")
    evidence_text = risk_flags.evidence[0].text.strip()
    if len(evidence_text) < 12:
        return _missing_field("special_terms")
    return _field(
        evidence_text[:500],
        "특약 후보",
        0.68,
        True,
        risk_flags.evidence,
    )


AXIS_LABELS: dict[str, tuple[str, ...]] = {
    "deposit_amount": ("보증금", "보승금", "보중금", "임대보증금"),
    "monthly_rent": ("월세", "차임", "월차임", "월 차임"),
    "lease_period": ("임대차기간", "임대차 기간", "존속기간", "기간"),
    "address": ("소재지", "소 제 지", "주소", "부동산의표시", "부동산의 표시"),
    "special_terms": ("특약", "특약사항", "특약 사항"),
}


def _merge_axis_candidates(
    fields: dict[str, ContractFieldValue],
    candidates: dict[str, ContractFieldValue],
) -> dict[str, ContractFieldValue]:
    merged: dict[str, ContractFieldValue] = {}
    for field_id, candidate in candidates.items():
        current = fields.get(field_id)
        if current is None or current.value in (None, "") or candidate.confidence > current.confidence:
            merged[field_id] = candidate
    return merged


def _infer_missing_payment_fields(fields: dict[str, ContractFieldValue]) -> None:
    if fields.get("balance_payment") and fields["balance_payment"].value not in (None, ""):
        return
    deposit = _numeric_field_value(fields.get("deposit_amount"))
    contract_payment = _numeric_field_value(fields.get("contract_payment"))
    intermediate_payment = _numeric_field_value(fields.get("intermediate_payment")) or 0
    if deposit is None or contract_payment is None:
        return
    balance = deposit - contract_payment - intermediate_payment
    if balance <= 0 or not _amount_in_expected_range("balance_payment", balance):
        return

    evidence = []
    for field_id in ("deposit_amount", "contract_payment", "intermediate_payment"):
        field = fields.get(field_id)
        if field and field.evidence:
            evidence.extend(field.evidence[:1])
    fields["balance_payment"] = _field(
        balance,
        _format_won(balance),
        0.72,
        True,
        evidence,
    )


def _repair_lease_period_from_text(fields: dict[str, ContractFieldValue], text: str) -> None:
    dates = _iter_noisy_dates(text)
    pair = _select_period_date_pair(dates)
    if not pair:
        return

    start, end = pair
    current_start = fields.get("lease_start_date")
    current_end = fields.get("lease_end_date")
    evidence = []
    if current_start and current_start.evidence:
        evidence = current_start.evidence
    elif current_end and current_end.evidence:
        evidence = current_end.evidence

    if current_start is None or current_start.value != start[1]:
        fields["lease_start_date"] = _field(start[1], start[1], 0.76, True, evidence)
    if current_end is None or current_end.value != end[1]:
        fields["lease_end_date"] = _field(end[1], end[1], 0.76, True, evidence)


def _repair_property_fields_from_text(fields: dict[str, ContractFieldValue], text: str) -> None:
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines() if line.strip()]
    repairs = {
        "land_area": _repair_land_area_display(lines),
        "building_info": _repair_building_info_display(lines),
        "lease_area": _repair_lease_area_display(lines),
    }
    for field_id, display in repairs.items():
        if not display:
            continue
        current = fields.get(field_id)
        evidence = current.evidence if current and current.evidence else []
        fields[field_id] = _field(display, display, 0.76, True, evidence)


def _repair_land_area_display(lines: list[str]) -> Optional[str]:
    best_line = _best_line(
        lines,
        required=("\ud1a0", "\uba74\uc801"),
        preferred=("\uc9c0\ubaa9", "\ub300"),
        needs_number=True,
    )
    if not best_line:
        return None
    best_line = _property_text_segment(best_line, "land_area") or best_line
    area = _extract_area_text(best_line)
    if area:
        return f"\ud1a0\uc9c0 \uc9c0\ubaa9 \ub300 \uba74\uc801 {area}\u33a1"
    return _trim_display_line(best_line)


def _repair_building_info_display(lines: list[str]) -> Optional[str]:
    best_line = _best_line(
        lines,
        required=("\uac74",),
        preferred=("\uad6c\uc870", "\uc6a9\ub3c4", "\ucf58\ud06c\ub9ac\ud2b8"),
        needs_number=False,
    )
    if not best_line:
        return None
    best_line = _property_text_segment(best_line, "building_info") or best_line
    structure = _extract_building_structure_text(best_line)
    area = _extract_area_text(best_line)
    if structure and area:
        return f"\uac74\ubb3c \uad6c\uc870\u00b7\uc6a9\ub3c4 {structure} \uba74\uc801 {area}\u33a1"
    if structure:
        return f"\uac74\ubb3c \uad6c\uc870\u00b7\uc6a9\ub3c4 {structure}"
    return _trim_display_line(best_line)


def _property_text_segment(text: str, field_id: str) -> Optional[str]:
    for candidate_field_id, segment in _split_property_line(text):
        if candidate_field_id == field_id:
            return segment
    return None


def _repair_lease_area_display(lines: list[str]) -> Optional[str]:
    best_line = _best_line(
        lines,
        required=("\uc784\ub300\ud560\ubd80\ubd84",),
        preferred=("\uc804\ubd80", "\ud638"),
        needs_number=False,
    )
    if not best_line:
        return None
    match = re.search(r"(\d+\s*\uce35\s*\d+\s*\ud638\s*\uc804\ubd80)", best_line)
    if match:
        value = re.sub(r"\s+", "", match.group(1))
        return f"\uc784\ub300\ud560\ubd80\ubd84 {value}"
    return _trim_display_line(best_line)


def _best_line(
    lines: list[str],
    required: tuple[str, ...],
    preferred: tuple[str, ...],
    needs_number: bool,
) -> Optional[str]:
    best: Optional[tuple[int, str]] = None
    for line in lines:
        compact = _compact(line)
        if not all(term in compact for term in required):
            continue
        if needs_number and not re.search(r"\d", line):
            continue
        score = sum(2 for term in preferred if term in compact)
        score += min(3, len(re.findall(r"\d", line)))
        if "[REDACTED]" in line:
            score -= 4
        if best is None or score > best[0]:
            best = (score, line)
    return best[1] if best else None


def _extract_area_text(text: str) -> Optional[str]:
    patterns = (
        r"면\s*적\s*([0-9]+(?:[.,]\d+)?)",
        r"([0-9]+(?:[.,]\d+)?)\s*(?:㎡|m2|m²)",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).replace(",", ".")
    return None


def _amount_distance_from_label(window: str) -> int:
    number_match = re.search(r"[0-9][0-9,./\\s]{3,}[0-9]", window)
    korean_match = re.search(r"[일이삼사오육칠팔구십백천만억\s]{2,}원", window)
    distances = [match.start() for match in (number_match, korean_match) if match]
    return min(distances) if distances else len(window)


def _extract_building_structure_text(text: str) -> Optional[str]:
    compact = re.sub(r"\s+", "", text)
    match = re.search(r"(?:구조[·ㆍ.]?용도|구조|용도)(.+?)(?:면적|m2|㎡|m\b|$)", compact)
    if not match:
        return None
    value = match.group(1).strip(" :：-/")
    value = re.sub(r"(?:면적|m2|㎡|m)$", "", value).strip(" :：-/")
    return value[:40] or None


def _trim_display_line(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()[:120]


def _numeric_field_value(field: Optional[ContractFieldValue]) -> Optional[int]:
    if field is None or field.value in (None, ""):
        return None
    if isinstance(field.value, bool):
        return None
    if isinstance(field.value, (int, float)):
        return int(field.value)
    digits = re.sub(r"\D", "", str(field.value))
    return int(digits) if digits else None


def _extract_axis_field_candidates(
    locations: list[ExtractedTextLocation],
) -> dict[str, ContractFieldValue]:
    if not locations:
        return {}

    lines = _group_axis_lines(locations)
    candidates: dict[str, ContractFieldValue] = {}
    table_candidates = _extract_payment_table_candidates(lines)
    candidates.update(table_candidates)
    property_candidates = _extract_property_display_candidates(lines)
    candidates.update(property_candidates)
    special_candidates = _extract_special_term_candidates(lines)
    candidates.update(special_candidates)

    for line_index, line in enumerate(lines):
        line_text = _line_text(line)
        right_context = _right_context_for_labels(line, AXIS_LABELS["deposit_amount"])
        if right_context:
            amount = _extract_amount_from_text(right_context[0])
            if amount is not None and _amount_in_expected_range("deposit_amount", amount):
                candidates["deposit_amount"] = _axis_field(
                    amount,
                    _format_won(amount),
                    0.86,
                    right_context[1],
                    "deposit_amount",
                )

        right_context = _right_context_for_labels(line, AXIS_LABELS["monthly_rent"])
        if right_context:
            amount = _extract_amount_from_text(right_context[0])
            if amount is not None and _amount_in_expected_range("monthly_rent", amount):
                candidates["monthly_rent"] = _axis_field(
                    amount,
                    _format_won(amount),
                    0.84,
                    right_context[1],
                    "monthly_rent",
                )

        if _line_has_label(line, AXIS_LABELS["lease_period"]):
            period_context = " ".join(
                _line_text(item)
                for item in lines[line_index : min(len(lines), line_index + 4)]
            )
            dates = list(_iter_dates(period_context)) or _iter_noisy_dates(period_context)
            dates = _prefer_period_dates(period_context, dates)
            if len(dates) >= 2 and dates[0][1] != dates[1][1]:
                evidence_locations = _merge_location_window(lines[line_index : min(len(lines), line_index + 4)])
                evidence = _axis_evidence(evidence_locations, "임대차기간", f"{dates[0][0]} {dates[1][0]}", 0.78)
                candidates["lease_start_date"] = _field(dates[0][1], dates[0][1], 0.78, False, evidence)
                candidates["lease_end_date"] = _field(dates[1][1], dates[1][1], 0.78, False, evidence)

        if _line_has_label(line, AXIS_LABELS["address"]):
            context_locations = _merge_location_window(lines[line_index : min(len(lines), line_index + 2)])
            context_text = " ".join(item.text for item in context_locations)
            address = _extract_address_candidate(context_text)
            if address:
                candidates["address"] = _axis_field(address, address, 0.74, context_locations, "address")

        if _line_has_label(line, AXIS_LABELS["special_terms"]):
            special_locations = _collect_special_term_locations(lines, line_index)
            special_text = " ".join(item.text for item in special_locations).strip()
            if len(special_text) >= 12:
                candidates["special_terms"] = _axis_field(
                    special_text[:500],
                    "특약 추출",
                    0.76,
                    special_locations,
                    "special_terms",
                )

    return candidates


def _extract_special_term_candidates(
    lines: list[list[ExtractedTextLocation]],
) -> dict[str, ContractFieldValue]:
    for index, line in enumerate(lines):
        compact = _compact(_line_text(line))
        if not _looks_like_special_term_start(compact):
            continue
        locations = _collect_special_term_locations(lines, index)
        text = re.sub(r"\s+", " ", " ".join(item.text for item in locations)).strip()
        if len(text) < 12:
            continue
        return {
            "special_terms": _axis_field(
                text[:500],
                "특약 추출",
                0.76,
                locations,
                "special_terms",
            )
        }
    return {}


def _looks_like_special_term_start(compact_text: str) -> bool:
    terms = (
        "특약",
        "특약사항",
        "원상복구",
        "수선비",
        "보증금반환",
        "반환지연",
        "중개보수",
        "증개보수",
    )
    return any(term in compact_text for term in terms)


def _extract_property_display_candidates(
    lines: list[list[ExtractedTextLocation]],
) -> dict[str, ContractFieldValue]:
    best_candidates: dict[str, ContractFieldValue] = {}
    best_score = 0
    page_numbers = sorted({line[0].page_number for line in lines if line})
    for page_number in page_numbers:
        page_lines = [line for line in lines if line and line[0].page_number == page_number]
        start = _find_property_display_start(page_lines)
        end = _find_contract_table_start(page_lines)
        if start is None or end is None or end <= start:
            continue

        page_candidates = _extract_property_geometry_candidates(
            page_lines[start + 1 : end]
        )
        for line in page_lines[start + 1 : end]:
            text = _line_text(line)
            for field_id, display in _property_fields_for_line(text):
                if field_id in page_candidates:
                    continue
                display = re.sub(r"\s+", " ", display).strip()
                if len(display) < 4:
                    continue
                page_candidates[field_id] = _axis_field(display[:160], display[:160], 0.74, line, field_id)

        score = sum(1 for key in ("land_area", "building_info", "lease_area") if key in page_candidates)
        if score > best_score:
            best_candidates = page_candidates
            best_score = score
        if score == 3:
            break
    return best_candidates


def _extract_property_geometry_candidates(
    property_lines: list[list[ExtractedTextLocation]],
) -> dict[str, ContractFieldValue]:
    locations = [item for line in property_lines for item in line]
    if not locations:
        return {}

    max_x = max(item.bbox[2] for item in locations)
    area_pattern = re.compile(r"\d+(?:[.,]\d+)?\s*(?:m|㎡)", re.IGNORECASE)
    area_locations = sorted(
        (
            item
            for item in locations
            if item.bbox[0] >= max_x * 0.65 and area_pattern.search(item.text)
        ),
        key=_y_center,
    )
    if len(area_locations) < 3:
        return {}
    area_locations = area_locations[:3]

    land_anchor = next(
        (item for item in locations if "토지" in _compact(item.text)),
        None,
    )
    lease_terms = ("임대할부분", "임대할", "임대부분", "임대합부분", "입대합부분")
    lease_anchor = next(
        (
            item
            for item in locations
            if any(term in _compact(item.text) for term in lease_terms)
        ),
        None,
    )
    if land_anchor is None or lease_anchor is None:
        return {}

    left_x_limit = min(land_anchor.bbox[0], lease_anchor.bbox[0]) + 45
    building_anchor_candidates = [
        item
        for item in locations
        if item not in (land_anchor, lease_anchor)
        and item.bbox[0] <= left_x_limit
        and _y_center(land_anchor) < _y_center(item) < _y_center(lease_anchor)
    ]
    building_left_y = (
        _y_center(min(building_anchor_candidates, key=lambda item: item.bbox[0]))
        if building_anchor_candidates
        else (_y_center(land_anchor) + _y_center(lease_anchor)) / 2
    )

    row_ids = ("land_area", "building_info", "lease_area")
    left_points = (
        (land_anchor.bbox[0], _y_center(land_anchor)),
        (land_anchor.bbox[0], building_left_y),
        (lease_anchor.bbox[0], _y_center(lease_anchor)),
    )
    right_points = tuple(
        ((item.bbox[0] + item.bbox[2]) / 2, _y_center(item))
        for item in area_locations
    )
    rows: dict[str, list[ExtractedTextLocation]] = {row_id: [] for row_id in row_ids}

    for item in locations:
        compact = _compact(item.text)
        if any(term in compact for term in ("소재지", "주소", "계약내용", "부동산의표시")):
            continue

        x_center = (item.bbox[0] + item.bbox[2]) / 2
        if x_center >= max_x * 0.65:
            field_id = row_ids[
                min(
                    range(len(area_locations)),
                    key=lambda index: abs(_y_center(item) - _y_center(area_locations[index])),
                )
            ]
        elif item is area_locations[0] or "토지" in compact or "지목" in compact:
            field_id = "land_area"
        elif item is area_locations[1] or any(
            term in compact for term in ("건물", "건문", "철근", "콘크리트", "주택", "구조", "용도")
        ):
            field_id = "building_info"
        elif item is area_locations[2] or any(term in compact for term in lease_terms):
            field_id = "lease_area"
        else:
            distances = []
            for row_index, row_id in enumerate(row_ids):
                left_x, left_y = left_points[row_index]
                right_x, right_y = right_points[row_index]
                ratio = 0.0 if right_x == left_x else (x_center - left_x) / (right_x - left_x)
                expected_y = left_y + max(0.0, min(1.0, ratio)) * (right_y - left_y)
                distances.append((abs(_y_center(item) - expected_y), row_id))
            distance, field_id = min(distances)
            if distance > 18:
                continue
        rows[field_id].append(item)

    candidates: dict[str, ContractFieldValue] = {}
    for field_id in row_ids:
        unique_row = {item.span_id: item for item in rows[field_id]}
        row = sorted(unique_row.values(), key=lambda item: item.bbox[0])
        if not row or area_locations[row_ids.index(field_id)] not in row:
            continue
        display_parts = [item.text for item in row]
        if field_id == "building_info" and not any(
            "건물" in _compact(part) or "건문" in _compact(part)
            for part in display_parts
        ):
            display_parts = [part for part in display_parts if not re.fullmatch(r"\d+", part.strip())]
            display_parts.insert(0, "건물")
        display = _normalize_property_display(" ".join(display_parts), field_id)
        candidates[field_id] = _axis_field(
            display[:160],
            display[:160],
            0.82,
            row,
            field_id,
        )
    return candidates


def _normalize_property_display(value: str, field_id: str) -> str:
    display = re.sub(r"\s+", " ", value).strip()
    display = re.sub(r"지\s*[iIl1]\s*목", "지목", display, flags=re.IGNORECASE)
    display = re.sub(r"\b구\s+조\b", "구조", display)
    display = re.sub(r"\b[0-9A-Za-z]?도(?=[가-힣]*주택)", "용도 ", display)
    display = re.sub(r"(?:연\s*)?면\s*적(?:\s*적)?", "면적", display)
    display = re.sub(r"\b면\s+(?=(?:약\s*)?\d)", "면적 ", display)
    display = re.sub(r"\b적\s+(?=(?:약\s*)?\d)", "면적 ", display)
    if field_id == "lease_area":
        display = re.sub(r"임대합부분", "임대할 부분", display)
    return re.sub(r"\s+", " ", display).strip()


def _find_property_display_start(lines: list[list[ExtractedTextLocation]]) -> Optional[int]:
    for index, line in enumerate(lines):
        compact = _compact(_line_text(line))
        if "부동산의표시" in compact or ("부동산" in compact and "표시" in compact):
            return index
    for index, line in enumerate(lines[:8]):
        compact = _compact(_line_text(line))
        if "소재지" in compact or "소제지" in compact:
            return max(0, index - 1)
    return None


def _property_field_for_line(text: str) -> Optional[str]:
    fields = _property_fields_for_line(text)
    return fields[0][0] if fields else None


def _property_fields_for_line(text: str) -> list[tuple[str, str]]:
    compact = _compact(text)
    if any(term in compact for term in ("소재지", "소제지", "주소")):
        return []

    segments = _split_property_line(text)
    if segments:
        return segments

    if "토지" in compact or "지목" in compact or "지면적" in compact:
        return [("land_area", text)]
    if "건물" in compact or "건문" in compact or ("구조" in compact and "용도" in compact):
        return [("building_info", text)]
    lease_terms = ("임대할부분", "임대할", "임대부분", "임대합부분", "입대합부분")
    if any(term in compact for term in lease_terms) or ("임대" in compact and "부분" in compact):
        return [("lease_area", text)]
    return []


def _split_property_line(text: str) -> list[tuple[str, str]]:
    labels = (
        ("land_area", r"토\s*지|지\s*목|지\s*면\s*적"),
        ("building_info", r"건\s*물|건\s*문|구\s*조|용\s*도"),
        ("lease_area", r"임\s*대\s*할\s*부\s*분|임\s*대\s*부\s*분|임\s*대\s*합\s*부\s*분|입\s*대\s*합\s*부\s*분"),
    )
    matches: list[tuple[int, str]] = []
    for field_id, pattern in labels:
        match = re.search(pattern, text)
        if match:
            matches.append((match.start(), field_id))
    matches.sort(key=lambda item: item[0])
    if len(matches) < 2:
        return []

    segments: list[tuple[str, str]] = []
    for index, (start, field_id) in enumerate(matches):
        end = matches[index + 1][0] if index + 1 < len(matches) else len(text)
        segment = text[start:end].strip(" :：,，/|")
        if len(_compact(segment)) >= 3:
            segments.append((field_id, segment))
    return segments


PAYMENT_ROW_FIELDS = (
    "deposit_amount",
    "contract_payment",
    "intermediate_payment",
    "balance_payment",
    "monthly_rent",
)


def _extract_payment_table_candidates(
    lines: list[list[ExtractedTextLocation]],
) -> dict[str, ContractFieldValue]:
    best_candidates: dict[str, ContractFieldValue] = {}
    best_score = 0

    page_numbers = sorted({line[0].page_number for line in lines if line})
    for page_number in page_numbers:
        page_lines = [line for line in lines if line and line[0].page_number == page_number]
        table_start = _find_contract_table_start(page_lines)
        if table_start is None:
            continue

        amount_rows: list[tuple[Optional[str], int, list[ExtractedTextLocation], int]] = []
        for line in page_lines[table_start + 1 : min(len(page_lines), table_start + 12)]:
            text = _line_text(line)
            if _looks_like_article_two(text):
                break
            amount = _best_amount_in_line(text)
            if amount is None:
                continue
            amount_rows.append((_payment_field_for_line(text), amount, line, _amount_quality(text, amount)))

        if len(amount_rows) < 2:
            continue

        page_candidates: dict[str, ContractFieldValue] = {}
        row_fields = _payment_row_fields_for_amounts(amount_rows)
        for fallback_field_id, (detected_field_id, amount, line, quality) in zip(row_fields, amount_rows):
            field_id = detected_field_id or fallback_field_id
            if field_id in page_candidates:
                continue
            if not _amount_in_expected_range(field_id, amount):
                continue
            confidence = min(0.9, 0.72 + quality * 0.03)
            page_candidates[field_id] = _axis_field(
                amount,
                _format_won(amount),
                confidence,
                line,
                field_id,
            )

        period = _extract_period_after_contract_table(page_lines, table_start)
        if period:
            start, end, evidence_locations = period
            evidence = _axis_evidence(evidence_locations, "임대차기간", f"{start[0]} {end[0]}", 0.8)
            page_candidates["lease_start_date"] = _field(start[1], start[1], 0.8, False, evidence)
            page_candidates["lease_end_date"] = _field(end[1], end[1], 0.8, False, evidence)

        score = len(page_candidates) + sum(1 for key in ("deposit_amount", "monthly_rent") if key in page_candidates)
        if score > best_score:
            best_candidates = page_candidates
            best_score = score

    return best_candidates


def _find_contract_table_start(lines: list[list[ExtractedTextLocation]]) -> Optional[int]:
    for index, line in enumerate(lines):
        text = _compact(_line_text(line))
        if "계약내용" in text and "2" in text:
            return index
    for index, line in enumerate(lines):
        text = _compact(_line_text(line))
        if "계약내용" in text:
            return index
    return None


def _payment_row_fields_for_amounts(
    amount_rows: list[tuple[Optional[str], int, list[ExtractedTextLocation], int]],
) -> tuple[str, ...]:
    if len(amount_rows) == 4:
        return ("deposit_amount", "contract_payment", "balance_payment", "monthly_rent")
    if len(amount_rows) == 3:
        return ("deposit_amount", "balance_payment", "monthly_rent")
    return PAYMENT_ROW_FIELDS[: len(amount_rows)]


def _payment_field_for_line(text: str) -> Optional[str]:
    compact = _compact(text)
    if "차임" in compact or ("차" in compact and "임" in compact):
        return "monthly_rent"
    if "계약금" in compact or ("계" in compact and "약" in compact and "금" in compact):
        return "contract_payment"
    if "중도금" in compact or ("중" in compact and "도" in compact and "금" in compact):
        return "intermediate_payment"
    if "잔금" in compact or ("잔" in compact and "금" in compact):
        return "balance_payment"
    if "보증금" in compact or "보중금" in compact or ("보" in compact and "금" in compact):
        return "deposit_amount"
    return None


def _looks_like_article_two(text: str) -> bool:
    compact = _compact(text)
    return "제2조" in compact or "존속기간" in compact or "존숙기간" in compact


def _best_amount_in_line(text: str) -> Optional[int]:
    amounts: list[int] = []
    for match in re.finditer(r"[0-9][0-9,./\\s]{3,}[0-9]", text):
        raw = match.group(0)
        digits = re.sub(r"\D", "", raw)
        if len(digits) >= 4:
            amounts.append(int(digits))
    korean_amount = _extract_amount_from_text(text)
    if korean_amount is not None:
        amounts.append(korean_amount)
    if not amounts:
        return None
    return max(amounts)


def _amount_quality(text: str, amount: int) -> int:
    quality = 0
    if "," in text:
        quality += 2
    if "W" in text or "원" in text or "정" in text:
        quality += 1
    if amount >= 100_000:
        quality += 1
    return quality


def _extract_period_after_contract_table(
    lines: list[list[ExtractedTextLocation]],
    table_start: int,
) -> Optional[tuple[tuple[str, str, int], tuple[str, str, int], list[ExtractedTextLocation]]]:
    for index, line in enumerate(lines[table_start + 1 : min(len(lines), table_start + 16)], start=table_start + 1):
        if not _looks_like_article_two(_line_text(line)):
            continue
        evidence_lines = lines[index : min(len(lines), index + 4)]
        context = " ".join(_line_text(item) for item in evidence_lines)
        dates = list(_iter_dates(context)) or _iter_noisy_dates(context)
        dates = _prefer_period_dates(context, dates)
        if len(dates) >= 2 and dates[0][1] != dates[1][1]:
            return dates[0], dates[1], _merge_location_window(evidence_lines)
    return None


def _group_axis_lines(locations: list[ExtractedTextLocation]) -> list[list[ExtractedTextLocation]]:
    sorted_locations = sorted(locations, key=lambda item: (item.page_number, _y_center(item), item.bbox[0]))
    lines: list[list[ExtractedTextLocation]] = []

    for location in sorted_locations:
        if not location.text or location.text == "[REDACTED]":
            continue
        if not lines:
            lines.append([location])
            continue

        last_line = lines[-1]
        same_page = last_line[0].page_number == location.page_number
        avg_height = sum(max(1.0, item.bbox[3] - item.bbox[1]) for item in last_line) / len(last_line)
        tolerance = max(10.0, avg_height * 0.75)
        if same_page and abs(_y_center(location) - _line_y_center(last_line)) <= tolerance:
            last_line.append(location)
        else:
            lines.append([location])

    return [sorted(line, key=lambda item: item.bbox[0]) for line in lines]


def _line_has_label(line: list[ExtractedTextLocation], labels: tuple[str, ...]) -> bool:
    compact_line = _compact(_line_text(line))
    return any(_compact(label) in compact_line for label in labels)


def _right_context_for_labels(
    line: list[ExtractedTextLocation],
    labels: tuple[str, ...],
) -> Optional[tuple[str, list[ExtractedTextLocation]]]:
    label_indexes = [
        index
        for index, item in enumerate(line)
        if any(_compact(label) in _compact(item.text) for label in labels)
    ]
    if not label_indexes and _line_has_label(line, labels):
        label_indexes = [0]
    if not label_indexes:
        return None

    label_index = label_indexes[-1]
    label_right = line[label_index].bbox[2]
    right_items = [
        item
        for item in line[label_index + 1 :]
        if item.bbox[0] >= label_right - 2
    ]
    if not right_items:
        return None
    return " ".join(item.text for item in right_items), right_items


def _axis_field(
    value: Union[str, int, float, bool, list, None],
    display_value: str,
    confidence: float,
    locations: list[ExtractedTextLocation],
    label_text: str,
) -> ContractFieldValue:
    return _field(
        value,
        display_value,
        confidence,
        confidence < 0.8,
        _axis_evidence(locations, label_text, display_value, confidence),
    )


def _axis_evidence(
    locations: list[ExtractedTextLocation],
    label_text: str,
    value_text: str,
    confidence: float,
) -> list[ContractFieldEvidence]:
    if not locations:
        return []
    ocr_values = [item.confidence for item in locations if item.confidence is not None]
    return [
        ContractFieldEvidence(
            page_number=locations[0].page_number,
            bbox=_union_bbox(locations),
            coordinate_system=locations[0].coordinate_system,
            span_ids=[item.span_id for item in locations],
            text=" ".join(item.text for item in locations),
            label_text=label_text,
            value_text=value_text,
            value_bbox=_union_bbox(locations),
            match_confidence=confidence,
            ocr_confidence=sum(ocr_values) / len(ocr_values) if ocr_values else None,
        )
    ]


def _collect_special_term_locations(
    lines: list[list[ExtractedTextLocation]],
    start_index: int,
) -> list[ExtractedTextLocation]:
    collected: list[ExtractedTextLocation] = []
    start_page = lines[start_index][0].page_number
    for line in lines[start_index : min(len(lines), start_index + 10)]:
        if line[0].page_number != start_page:
            break
        text = _compact(_line_text(line))
        if collected and any(stop in text for stop in ("임대인", "임차인", "중개", "성명", "주소", "전화")):
            break
        collected.extend(line)
    return collected


def _extract_address_candidate(text: str) -> Optional[str]:
    cleaned = re.sub(r"\s+", " ", text).strip()
    match = re.search(
        r"((?:서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|"
        r"충청|충북|충남|전라|전북|전남|경상|경북|경남|제주|전주)[^\\n]{4,80})",
        cleaned,
    )
    if match:
        value = _trim_property_tail(match.group(1)).strip(" ,.")
        return value if _looks_like_address(_compact(value)) else None
    return None


def _trim_property_tail(value: str) -> str:
    return re.split(r"\s+(?:토\s*지|건\s*물|임대할\s*부분|임대할부분)\b", value, maxsplit=1)[0]


def _merge_location_window(lines: list[list[ExtractedTextLocation]]) -> list[ExtractedTextLocation]:
    return [item for line in lines for item in line]


def _line_text(line: list[ExtractedTextLocation]) -> str:
    return " ".join(item.text for item in line)


def _y_center(location: ExtractedTextLocation) -> float:
    return (location.bbox[1] + location.bbox[3]) / 2


def _line_y_center(line: list[ExtractedTextLocation]) -> float:
    return sum(_y_center(item) for item in line) / len(line)


def _extract_amount_from_text(text: str) -> Optional[int]:
    number_match = re.search(r"([0-9][0-9,]{3,})", text)
    if number_match:
        return int(re.sub(r"\D", "", number_match.group(1)))
    readable_korean_amount = _extract_korean_amount_from_text(text)
    if readable_korean_amount is not None:
        return readable_korean_amount

    korean_match = re.search(r"([일이삼사오육륙칠팔구십백천만억한공영\s]+)원?", text)
    if korean_match:
        return _parse_korean_amount(korean_match.group(1))
    return None


def _amount_in_expected_range(field_id: str, amount: int) -> bool:
    if field_id in {"deposit_amount", "sale_price"}:
        return 1_000_000 <= amount <= 10_000_000_000
    if field_id in {"monthly_rent", "maintenance_fee"}:
        return 10_000 <= amount <= 20_000_000
    if field_id in {"contract_payment", "intermediate_payment", "balance_payment"}:
        return 100_000 <= amount <= 10_000_000_000
    return amount > 0


def _looks_like_address(value: str) -> bool:
    if not value or "표시" in value or "사무소" in value:
        return False
    region_hit = re.search(
        r"서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충청|충북|충남|"
        r"전라|전북|전남|경상|경북|경남|제주|"
        r"전주|수원|성남|고양|용인|창원|청주|천안",
        value,
    )
    road_hit = re.search(r"[가-힣0-9]+(로|길|동|읍|면|구|군)\d*", value)
    return bool(region_hit and road_hit)


def _clean_address_value(value: str) -> str:
    value = re.sub(r"^\s*(?:소\s*재\s*지|주\s*소|부\s*동\s*산\s*의?\s*표\s*시)\s*[:：]?", "", value)
    return _strip_property_suffix(value).strip(" :：,，/|")


def _strip_property_suffix(value: str) -> str:
    return re.split(
        r"\s*(?:토\s*지|건\s*물|건\s*문|임\s*대\s*할\s*부\s*분|임\s*대\s*부\s*분)\s*[:：]?",
        value,
        maxsplit=1,
    )[0]


def _parse_korean_amount(value: str) -> Optional[int]:
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


READABLE_KOREAN_DIGITS = {
    "\uc601": 0,
    "\uacf5": 0,
    "\uc77c": 1,
    "\ud55c": 1,
    "\uc774": 2,
    "\ub450": 2,
    "\uc0bc": 3,
    "\uc0ac": 4,
    "\uc624": 5,
    "\uc721": 6,
    "\ub959": 6,
    "\uce60": 7,
    "\ud314": 8,
    "\uad6c": 9,
}
READABLE_SMALL_UNITS = {"\uc2ed": 10, "\ubc31": 100, "\ucc9c": 1000}
READABLE_LARGE_UNITS = {"\ub9cc": 10_000, "\uc5b5": 100_000_000}
READABLE_AMOUNT_CHARS = "".join(
    list(READABLE_KOREAN_DIGITS)
    + list(READABLE_SMALL_UNITS)
    + list(READABLE_LARGE_UNITS)
    + ["\uae08", "\uc6d0", "\uc815"]
)


def _extract_korean_amount_from_text(text: str) -> Optional[int]:
    candidates: list[int] = []
    pattern = re.compile(rf"[\s{re.escape(READABLE_AMOUNT_CHARS)}]{{2,}}")
    for match in pattern.finditer(text):
        amount = _parse_readable_korean_amount(match.group(0))
        if amount is not None:
            candidates.append(amount)
    return max(candidates) if candidates else None


def _parse_readable_korean_amount(value: str) -> Optional[int]:
    compact_value = re.sub(r"[\s,·ㆍ:：()]", "", value or "")
    compact_value = re.sub(r"^(?:\uc77c\uae08|\uae08)", "", compact_value)
    compact_value = re.sub(r"(?:\uc6d0|\uc815)$", "", compact_value)
    if not compact_value or not any(unit in compact_value for unit in READABLE_LARGE_UNITS):
        return None

    total = 0
    section = 0
    number = 0
    found = False
    for char in compact_value:
        if char in READABLE_KOREAN_DIGITS:
            number = READABLE_KOREAN_DIGITS[char]
            found = True
            continue
        if char in READABLE_SMALL_UNITS:
            section += (number or 1) * READABLE_SMALL_UNITS[char]
            number = 0
            found = True
            continue
        if char in READABLE_LARGE_UNITS:
            section += number
            total += (section or 1) * READABLE_LARGE_UNITS[char]
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


def _iter_noisy_dates(text: str) -> list[tuple[str, str, int]]:
    dates: list[tuple[str, str, int]] = []
    normalized_text = _normalize_date_ocr_text(text)
    pattern = re.compile(r"(20\d{2})[^0-9]{0,12}(\d{1,2})[^0-9]{0,12}(\d{1,2})")
    for match in pattern.finditer(normalized_text):
        year, month, day = match.groups()
        month_value = int(month)
        day_value = int(day)
        if not (1 <= month_value <= 12 and 1 <= day_value <= 31):
            continue
        dates.append((match.group(0), f"{year}.{month_value:02d}.{day_value:02d}", match.start()))
    return dates


def _prefer_period_dates(
    text: str,
    dates: list[tuple[str, str, int]],
) -> list[tuple[str, str, int]]:
    relevant_text, relevant_offset = _period_relevant_text(text)
    if relevant_offset:
        relevant_dates = [
            (raw, value, pos - relevant_offset)
            for raw, value, pos in dates
            if pos >= relevant_offset
        ]
        if len(relevant_dates) >= 2:
            dates = relevant_dates
            text = relevant_text
    pair = _select_period_date_pair(dates)
    if pair:
        return list(pair)
    if len(dates) < 3:
        return dates
    normalized = _normalize_date_ocr_text(text)
    anchor_positions = [
        match.start()
        for match in re.finditer(r"상태로|인도하며|인도일|임대차\s*기간|기간은|부터|까지", normalized)
    ]
    if not anchor_positions:
        return dates
    filtered = [
        date
        for date in dates
        if min(abs(date[2] - anchor) for anchor in anchor_positions) <= 120
    ]
    if len(filtered) >= 2:
        return filtered
    return dates[-2:]


def _period_relevant_text(text: str) -> tuple[str, int]:
    normalized = _normalize_date_ocr_text(text)
    anchors: list[int] = []
    for pattern in (r"2\s*조", r"제\s*2", r"존속\s*기간", r"기간"):
        match = re.search(pattern, normalized)
        if match:
            anchors.append(match.start())
    if not anchors:
        return text, 0
    offset = min(anchors)
    return text[offset:], offset


def _select_period_date_pair(
    dates: list[tuple[str, str, int]],
) -> Optional[tuple[tuple[str, str, int], tuple[str, str, int]]]:
    parsed = []
    for item in dates:
        date = _parse_yyyy_mm_dd(item[1])
        if date is not None:
            parsed.append((date, item))

    best: Optional[tuple[int, tuple[tuple[str, str, int], tuple[str, str, int]]]] = None
    for left_index, (left_date, left_item) in enumerate(parsed):
        left_year, left_month, left_day = left_date
        for right_date, right_item in parsed[left_index + 1 :]:
            right_year, right_month, right_day = right_date
            if right_year <= left_year:
                continue
            year_gap = right_year - left_year
            if not (1 <= year_gap <= 5):
                continue

            score = 0
            if left_month == right_month:
                score += 3
            if left_day == right_day:
                score += 3
            if left_year >= 2026:
                score += 2
            if 1 <= year_gap <= 3:
                score += 2
            score -= abs(left_item[2] - right_item[2]) // 80
            if best is None or score > best[0]:
                best = (score, (left_item, right_item))

    if best and best[0] >= 4:
        return best[1]
    return None


def _parse_yyyy_mm_dd(value: str) -> Optional[tuple[int, int, int]]:
    match = re.match(r"(\d{4})\.(\d{2})\.(\d{2})$", value)
    if not match:
        return None
    year, month, day = (int(part) for part in match.groups())
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return None
    return year, month, day


def _normalize_date_ocr_text(text: str) -> str:
    normalized = text.replace("_", " ").replace("|", " ")
    normalized = re.sub(r"(?<=\d)\s*[원권]\s*(?=\d{1,2}\s*[일인])", " 월 ", normalized)
    normalized = re.sub(r"(?<=\d)\s*[인]\b", " 일", normalized)
    return normalized


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
    value_text: Union[str, int, float, bool, list, None],
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
    value: Union[str, int, float, bool, list, None],
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
