from __future__ import annotations
from typing import Union, Optional

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
    fields["confirmed_date_status"] = _status_field(text, locations, "confirmed_date_status", ("확정일자",))
    fields["move_in_report_status"] = _status_field(text, locations, "move_in_report_status", ("전입신고", "주민등록"))
    fields["priority_rights"] = _status_field(text, locations, "priority_rights", ("선순위", "근저당", "가압류", "압류"))
    fields["special_terms"] = _special_terms_field(text, locations)
    fields["risk_flags"] = _risk_flags_field(text, locations)
    axis_candidates = _extract_axis_field_candidates(locations)
    if locations:
        for amount_field_id in ("deposit_amount", "monthly_rent", "sale_price"):
            if amount_field_id in fields and amount_field_id not in axis_candidates:
                fields[amount_field_id] = _missing_field(amount_field_id)
    fields.update(_merge_axis_candidates(fields, axis_candidates))
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
    label_pattern = "|".join(re.escape(_compact(label)) for label in labels)
    window_pattern = re.compile(rf"({label_pattern})(.{{0,90}})")
    for match in window_pattern.finditer(search_text):
        window = match.group(2)
        amount = _extract_amount_from_text(window)
        if amount is None:
            continue
        if not _amount_in_expected_range(field_id, amount):
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
    for line in lines:
        compact_line = _compact(line)
        if "사무소" in compact_line or "중개사무소" in compact_line:
            continue
        if not any(_compact(label) in compact_line for label in label_terms):
            continue
        if not _looks_like_address(compact_line):
            continue
        address_match = re.search(r"(?:소재지|주소)\s*[:：]?\s*(.{4,80})", line)
        value = address_match.group(1).strip() if address_match else line[:80]
        if not _looks_like_address(_compact(value)):
            continue
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


def _extract_axis_field_candidates(
    locations: list[ExtractedTextLocation],
) -> dict[str, ContractFieldValue]:
    if not locations:
        return {}

    lines = _group_axis_lines(locations)
    candidates: dict[str, ContractFieldValue] = {}
    table_candidates = _extract_payment_table_candidates(lines)
    candidates.update(table_candidates)

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
                for item in lines[line_index : min(len(lines), line_index + 3)]
            )
            dates = list(_iter_dates(period_context)) or _iter_noisy_dates(period_context)
            if len(dates) >= 2 and dates[0][1] != dates[1][1]:
                evidence_locations = _merge_location_window(lines[line_index : min(len(lines), line_index + 3)])
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

        amount_rows: list[tuple[int, list[ExtractedTextLocation], int]] = []
        for line in page_lines[table_start + 1 : min(len(page_lines), table_start + 12)]:
            text = _line_text(line)
            if _looks_like_article_two(text):
                break
            amount = _best_amount_in_line(text)
            if amount is None:
                continue
            amount_rows.append((amount, line, _amount_quality(text, amount)))

        if len(amount_rows) < 2:
            continue

        page_candidates: dict[str, ContractFieldValue] = {}
        row_fields = _payment_row_fields_for_amounts(amount_rows)
        for field_id, (amount, line, quality) in zip(row_fields, amount_rows):
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
    amount_rows: list[tuple[int, list[ExtractedTextLocation], int]],
) -> tuple[str, ...]:
    if len(amount_rows) == 4:
        return ("deposit_amount", "contract_payment", "balance_payment", "monthly_rent")
    if len(amount_rows) == 3:
        return ("deposit_amount", "balance_payment", "monthly_rent")
    return PAYMENT_ROW_FIELDS[: len(amount_rows)]


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
        evidence_lines = lines[index : min(len(lines), index + 3)]
        context = " ".join(_line_text(item) for item in evidence_lines)
        dates = list(_iter_dates(context)) or _iter_noisy_dates(context)
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
) -> tuple[str, list[ExtractedTextLocation]] | None:
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
    value: Optional[Union[str, int, float, bool, list]],
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
    match = re.search(r"((?:서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충청|전라|경상|제주|전주)[^\\n]{4,80})", cleaned)
    if match:
        value = match.group(1).strip(" ,.")
        return value if _looks_like_address(_compact(value)) else None
    return None


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
        r"서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충청|전라|경상|제주|"
        r"전주|수원|성남|고양|용인|창원|청주|천안",
        value,
    )
    road_hit = re.search(r"[가-힣0-9]+(로|길|동|읍|면|구|군)\d*", value)
    return bool(region_hit and road_hit)


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


def _iter_dates(text: str):
    pattern = re.compile(r"(\d{4})\s*[년./-]\s*(\d{1,2})\s*[월./-]\s*(\d{1,2})")
    for match in pattern.finditer(text):
        year, month, day = match.groups()
        yield match.group(0), f"{year}.{int(month):02d}.{int(day):02d}", match.start()


def _iter_noisy_dates(text: str) -> list[tuple[str, str, int]]:
    dates: list[tuple[str, str, int]] = []
    pattern = re.compile(r"(20\d{2})[^0-9]{0,8}(\d{1,2})[^0-9]{0,8}(\d{1,2})")
    for match in pattern.finditer(text):
        year, month, day = match.groups()
        month_value = int(month)
        day_value = int(day)
        if not (1 <= month_value <= 12 and 1 <= day_value <= 31):
            continue
        dates.append((match.group(0), f"{year}.{month_value:02d}.{day_value:02d}", match.start()))
    return dates


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
    value_text: Optional[Union[str, int, float, bool, list]],
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
    value: Optional[Union[str, int, float, bool, list]],
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
