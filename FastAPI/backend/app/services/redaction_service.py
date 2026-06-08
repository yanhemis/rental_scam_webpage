from __future__ import annotations

import re
from dataclasses import dataclass
from itertools import count

from app.config import get_settings
from app.schemas.extraction_schema import (
    ExtractedTextLocation,
    ExtractionResult,
    MaskStyle,
    RedactionDetectionMethod,
    RedactionMetrics,
    RedactionSensitivity,
    RedactionTarget,
)

REDACTED_TEXT = "[REDACTED]"
HIGH_SENSITIVITY_TYPES = {
    "resident_registration_number",
    "lessor_resident_registration_number",
    "lessee_resident_registration_number",
    "phone",
    "lessor_phone",
    "lessee_phone",
    "broker_phone",
    "account_number",
}
MEDIUM_SENSITIVITY_TYPES = {
    "name",
    "lessor_name",
    "lessee_name",
    "broker_name",
    "address",
    "lessor_address",
    "lessee_address",
    "broker_office",
    "broker_registration_number",
}


@dataclass(frozen=True)
class SensitiveLabel:
    label_type: str
    terms: tuple[str, ...]
    mask_right_ratio: float = 0.85


@dataclass(frozen=True)
class TemplateRedactionBox:
    label_type: str
    bbox_ratio: tuple[float, float, float, float]


SENSITIVE_LABELS = (
    SensitiveLabel("resident_registration_number", ("주민등록번호", "주민번호", "등록번호")),
    SensitiveLabel("phone", ("전화", "연락처", "휴대전화", "휴대폰")),
    SensitiveLabel("name", ("성명", "이름", "대표")),
    SensitiveLabel("address", ("주소",)),
    SensitiveLabel("account_number", ("계좌번호", "계좌")),
)

SENSITIVE_PATTERNS = (
    (re.compile(r"\d{6}\s*-\s*\d{7}"), "resident_registration_number"),
    (re.compile(r"01[016789]\s*[-.]?\s*\d{3,4}\s*[-.]?\s*\d{4}"), "phone"),
    (re.compile(r"\d{2,6}\s*[-.]?\s*\d{2,6}\s*[-.]?\s*\d{2,8}"), "account_number"),
)

READABLE_SENSITIVE_LABELS = (
    SensitiveLabel("resident_registration_number", ("주민등록번호", "주민번호", "등록번호")),
    SensitiveLabel("phone", ("전화", "연락처", "휴대전화", "휴대폰")),
    SensitiveLabel("name", ("성명", "이름", "대표")),
    SensitiveLabel("address", ("주소",)),
    SensitiveLabel("account_number", ("계좌번호", "계좌")),
)

STANDARD_CONTRACT_TEMPLATE_SIZE = (2382.0, 3368.0)


def _ratio_box(x0: float, y0: float, x1: float, y1: float) -> tuple[float, float, float, float]:
    width, height = STANDARD_CONTRACT_TEMPLATE_SIZE
    return (x0 / width, y0 / height, x1 / width, y1 / height)


STANDARD_CONTRACT_TEMPLATE_BOXES = (
    TemplateRedactionBox("account_number", _ratio_box(520, 2070, 1550, 2145)),
    TemplateRedactionBox("lessor_address", _ratio_box(500, 2220, 1185, 2295)),
    TemplateRedactionBox("lessor_resident_registration_number", _ratio_box(500, 2295, 1190, 2365)),
    TemplateRedactionBox("lessor_phone", _ratio_box(1240, 2295, 1595, 2365)),
    TemplateRedactionBox("lessor_name", _ratio_box(1670, 2295, 2050, 2365)),
    TemplateRedactionBox("lessee_address", _ratio_box(500, 2390, 1185, 2465)),
    TemplateRedactionBox("lessee_resident_registration_number", _ratio_box(500, 2465, 1190, 2540)),
    TemplateRedactionBox("lessee_phone", _ratio_box(1240, 2465, 1595, 2540)),
    TemplateRedactionBox("lessee_name", _ratio_box(1670, 2465, 2050, 2540)),
    TemplateRedactionBox("broker_office", _ratio_box(500, 2630, 1185, 2705)),
    TemplateRedactionBox("broker_office", _ratio_box(1240, 2630, 2050, 2705)),
    TemplateRedactionBox("broker_name", _ratio_box(500, 2720, 1185, 2795)),
    TemplateRedactionBox("broker_name", _ratio_box(1240, 2720, 2050, 2795)),
    TemplateRedactionBox("broker_registration_number", _ratio_box(500, 2800, 840, 2875)),
    TemplateRedactionBox("broker_phone", _ratio_box(900, 2800, 1185, 2875)),
    TemplateRedactionBox("broker_registration_number", _ratio_box(1240, 2800, 1595, 2875)),
    TemplateRedactionBox("broker_phone", _ratio_box(1670, 2800, 2050, 2875)),
)


def _bbox_union(locations: list[ExtractedTextLocation]) -> list[float]:
    return [
        min(item.bbox[0] for item in locations),
        min(item.bbox[1] for item in locations),
        max(item.bbox[2] for item in locations),
        max(item.bbox[3] for item in locations),
    ]


def _bbox_intersects(left: list[float], right: list[float]) -> bool:
    return not (
        left[2] <= right[0]
        or left[0] >= right[2]
        or left[3] <= right[1]
        or left[1] >= right[3]
    )


def _bbox_intersection_area(left: list[float], right: list[float]) -> float:
    x_overlap = max(0.0, min(left[2], right[2]) - max(left[0], right[0]))
    y_overlap = max(0.0, min(left[3], right[3]) - max(left[1], right[1]))
    return x_overlap * y_overlap


def _bbox_area(box: list[float]) -> float:
    return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])


def _bbox_overlap_ratio(left: list[float], right: list[float]) -> float:
    intersection = _bbox_intersection_area(left, right)
    denominator = min(_bbox_area(left), _bbox_area(right))
    if denominator <= 0:
        return 0.0
    return intersection / denominator


def _sensitivity_for(label_type: str) -> RedactionSensitivity:
    if label_type in HIGH_SENSITIVITY_TYPES:
        return RedactionSensitivity.high
    if label_type in MEDIUM_SENSITIVITY_TYPES:
        return RedactionSensitivity.medium
    return RedactionSensitivity.low


def _mask_style_for(sensitivity: RedactionSensitivity) -> MaskStyle:
    if sensitivity == RedactionSensitivity.high:
        return MaskStyle.opaque
    if sensitivity == RedactionSensitivity.medium:
        return MaskStyle.mosaic
    return MaskStyle.translucent


def _opacity_for(mask_style: MaskStyle) -> float:
    if mask_style == MaskStyle.translucent:
        return 0.35
    return 1.0


def _needs_review(confidence: float, detection_method: RedactionDetectionMethod) -> bool:
    if detection_method == RedactionDetectionMethod.template:
        return confidence < 0.85
    return confidence < 0.75


def _build_redaction_target(
    *,
    redaction_id: str,
    label_type: str,
    label_text: str,
    page_number: int,
    label_bbox: list[float],
    value_bbox: list[float],
    coordinate_system: str,
    confidence: float,
    box_confidence: float,
    text_confidence: float | None,
    detection_method: RedactionDetectionMethod,
) -> RedactionTarget:
    sensitivity = _sensitivity_for(label_type)
    mask_style = _mask_style_for(sensitivity)
    return RedactionTarget(
        redaction_id=redaction_id,
        label_type=label_type,
        label_text=label_text,
        page_number=page_number,
        label_bbox=label_bbox,
        value_bbox=value_bbox,
        coordinate_system=coordinate_system,
        confidence=confidence,
        box_confidence=box_confidence,
        text_confidence=text_confidence,
        detection_method=detection_method,
        sensitivity=sensitivity,
        mask_style=mask_style,
        opacity=_opacity_for(mask_style),
        needs_review=_needs_review(confidence, detection_method),
    )


def _text(value: object) -> str:
    if isinstance(value, list):
        return " ".join(_text(item) for item in value)
    return str(value or "")


def _average_location_confidence(locations: list[ExtractedTextLocation]) -> float | None:
    values = [item.confidence for item in locations if item.confidence is not None]
    if not values:
        return None
    return round(sum(values) / len(values), 3)


def _group_lines(locations: list[ExtractedTextLocation]) -> list[list[ExtractedTextLocation]]:
    sorted_locations = sorted(locations, key=lambda item: (item.page_number, item.bbox[1], item.bbox[0]))
    lines: list[list[ExtractedTextLocation]] = []

    for location in sorted_locations:
        y_center = (location.bbox[1] + location.bbox[3]) / 2
        height = max(1.0, location.bbox[3] - location.bbox[1])
        if not lines:
            lines.append([location])
            continue

        last_line = lines[-1]
        last_center = sum((item.bbox[1] + item.bbox[3]) / 2 for item in last_line) / len(last_line)
        same_page = last_line[0].page_number == location.page_number
        if same_page and abs(y_center - last_center) <= max(12.0, height * 0.65):
            last_line.append(location)
        else:
            lines.append([location])

    return [sorted(line, key=lambda item: item.bbox[0]) for line in lines]


def _compact_text(locations: list[ExtractedTextLocation]) -> str:
    return "".join("".join(_text(item.text).split()) for item in locations)


def _page_coordinate_extents(locations: list[ExtractedTextLocation]) -> dict[int, tuple[float, float]]:
    extents: dict[int, tuple[float, float]] = {}
    page_numbers = {item.page_number for item in locations}
    for page_number in page_numbers:
        page_locations = [item for item in locations if item.page_number == page_number]
        max_x = max((item.bbox[2] for item in page_locations), default=STANDARD_CONTRACT_TEMPLATE_SIZE[0])
        max_y = max((item.bbox[3] for item in page_locations), default=STANDARD_CONTRACT_TEMPLATE_SIZE[1])
        # OCR text rarely touches the page edge, so keep at least the template aspect size.
        extents[page_number] = (
            max(max_x, STANDARD_CONTRACT_TEMPLATE_SIZE[0]),
            max(max_y, STANDARD_CONTRACT_TEMPLATE_SIZE[1]),
        )
    return extents


def _detect_template_redactions(locations: list[ExtractedTextLocation]) -> list[RedactionTarget]:
    settings = get_settings()
    if not settings.privacy_template_redaction_enabled or not locations:
        return []

    extents = _page_coordinate_extents(locations)
    coordinate_system_by_page = {
        page: next(
            (item.coordinate_system for item in locations if item.page_number == page),
            "source",
        )
        for page in extents
    }
    redactions: list[RedactionTarget] = []
    redaction_ids = count(1)

    for page_number in sorted(extents):
        # Page 1 is usually the blank standard form in the MVP sample. From page 2 onward
        # the same standard-contract party/broker blocks are masked by template.
        if page_number == 1:
            continue

        page_width, page_height = extents[page_number]
        for template_box in STANDARD_CONTRACT_TEMPLATE_BOXES:
            x0_ratio, y0_ratio, x1_ratio, y1_ratio = template_box.bbox_ratio
            value_bbox = [
                x0_ratio * page_width,
                y0_ratio * page_height,
                x1_ratio * page_width,
                y1_ratio * page_height,
            ]
            redactions.append(
                _build_redaction_target(
                    redaction_id=f"template-{next(redaction_ids)}",
                    label_type=template_box.label_type,
                    label_text="standard_contract_template",
                    page_number=page_number,
                    label_bbox=value_bbox,
                    value_bbox=value_bbox,
                    coordinate_system=coordinate_system_by_page[page_number],
                    confidence=0.9,
                    box_confidence=0.92,
                    text_confidence=None,
                    detection_method=RedactionDetectionMethod.template,
                )
            )

    return redactions


def _find_label(line: list[ExtractedTextLocation]) -> tuple[SensitiveLabel, list[ExtractedTextLocation]] | None:
    compact = _compact_text(line)
    if not compact:
        return None

    for label in READABLE_SENSITIVE_LABELS:
        for term in label.terms:
            compact_term = "".join(term.split())
            if compact_term not in compact:
                continue

            label_chars = len(compact_term)
            matched: list[ExtractedTextLocation] = []
            seen = ""
            for location in line:
                seen += "".join(_text(location.text).split())
                matched.append(location)
                if compact_term in seen:
                    return label, matched[-max(1, min(len(matched), label_chars)) :]
    return None


def _line_value_bbox(
    line: list[ExtractedTextLocation],
    label_locations: list[ExtractedTextLocation],
    *,
    page_max_x: float,
) -> list[float] | None:
    label_bbox = _bbox_union(label_locations)
    line_bbox = _bbox_union(line)
    right_candidates = [item for item in line if item.bbox[0] >= label_bbox[2] - 2]

    if right_candidates:
        value_bbox = _bbox_union(right_candidates)
        value_bbox[0] = max(label_bbox[2], value_bbox[0])
        return value_bbox

    return [
        label_bbox[2],
        line_bbox[1],
        max(label_bbox[2] + 40, page_max_x),
        line_bbox[3],
    ]


def _detect_label_redactions(locations: list[ExtractedTextLocation]) -> list[RedactionTarget]:
    if not locations:
        return []

    page_max_x = {
        page: max(item.bbox[2] for item in locations if item.page_number == page)
        for page in {item.page_number for item in locations}
    }
    redaction_ids = count(1)
    redactions: list[RedactionTarget] = []

    for line in _group_lines(locations):
        label_match = _find_label(line)
        if label_match is None:
            continue

        label, label_locations = label_match
        label_bbox = _bbox_union(label_locations)
        value_bbox = _line_value_bbox(
            line,
            label_locations,
            page_max_x=page_max_x[line[0].page_number],
        )
        if value_bbox is None or value_bbox[2] <= value_bbox[0]:
            continue

        redactions.append(
            _build_redaction_target(
                redaction_id=f"redact-{next(redaction_ids)}",
                label_type=label.label_type,
                label_text="".join(_text(item.text) for item in label_locations),
                page_number=line[0].page_number,
                label_bbox=label_bbox,
                value_bbox=value_bbox,
                coordinate_system=line[0].coordinate_system,
                confidence=0.72,
                box_confidence=0.68,
                text_confidence=_average_location_confidence(label_locations),
                detection_method=RedactionDetectionMethod.ocr_label,
            )
        )

    return redactions


def _detect_regex_redactions(locations: list[ExtractedTextLocation]) -> list[RedactionTarget]:
    redactions: list[RedactionTarget] = []
    redaction_index = 1000
    for line in _group_lines(locations):
        joined = " ".join(_text(item.text) for item in line)
        for pattern, label_type in SENSITIVE_PATTERNS:
            if not pattern.search(joined):
                continue
            redactions.append(
                _build_redaction_target(
                    redaction_id=f"redact-{redaction_index}",
                    label_type=label_type,
                    label_text="regex",
                    page_number=line[0].page_number,
                    label_bbox=_bbox_union(line[:1]),
                    value_bbox=_bbox_union(line),
                    coordinate_system=line[0].coordinate_system,
                    confidence=0.64,
                    box_confidence=0.6,
                    text_confidence=_average_location_confidence(line),
                    detection_method=RedactionDetectionMethod.regex,
                )
            )
            redaction_index += 1
    return redactions


def _append_non_overlapping(
    base: list[RedactionTarget],
    candidates: list[RedactionTarget],
    *,
    min_overlap_ratio: float = 0.5,
) -> list[RedactionTarget]:
    merged = list(base)
    next_id = count(len(merged) + 1)
    for candidate in candidates:
        overlaps = any(
            existing.page_number == candidate.page_number
            and _bbox_overlap_ratio(existing.value_bbox, candidate.value_bbox) >= min_overlap_ratio
            for existing in merged
        )
        if overlaps:
            continue
        merged.append(
            candidate.model_copy(
                update={
                    "redaction_id": candidate.redaction_id
                    if candidate.redaction_id.startswith("template-")
                    else f"redact-{next(next_id)}"
                }
            )
        )
    return merged


def _rebuild_text(locations: list[ExtractedTextLocation]) -> str:
    pages: dict[int, list[ExtractedTextLocation]] = {}
    for location in locations:
        pages.setdefault(location.page_number, []).append(location)

    page_texts: list[str] = []
    for page in sorted(pages):
        lines = _group_lines(pages[page])
        page_texts.append("\n".join(" ".join(_text(item.text) for item in line) for line in lines))
    return "\n\n".join(page_texts).strip()


def _build_redaction_metrics(
    redactions: list[RedactionTarget],
    locations: list[ExtractedTextLocation],
) -> RedactionMetrics:
    if not redactions:
        return RedactionMetrics()

    return RedactionMetrics(
        total_redaction_count=len(redactions),
        template_redaction_count=sum(
            1 for item in redactions if item.detection_method == RedactionDetectionMethod.template
        ),
        ocr_label_redaction_count=sum(
            1 for item in redactions if item.detection_method == RedactionDetectionMethod.ocr_label
        ),
        regex_redaction_count=sum(
            1 for item in redactions if item.detection_method == RedactionDetectionMethod.regex
        ),
        redacted_location_count=sum(1 for item in locations if item.is_redacted),
        average_box_confidence=round(
            sum(item.box_confidence for item in redactions) / len(redactions),
            3,
        ),
        needs_review_count=sum(1 for item in redactions if item.needs_review),
    )


def apply_privacy_redactions(result: ExtractionResult) -> ExtractionResult:
    redactions = _detect_template_redactions(result.locations)
    redactions = _append_non_overlapping(redactions, _detect_label_redactions(result.locations))
    redactions = _append_non_overlapping(redactions, _detect_regex_redactions(result.locations))
    if not redactions:
        return result

    redaction_by_span: dict[str, tuple[str, str]] = {}
    for location in result.locations:
        for redaction in redactions:
            if location.page_number != redaction.page_number:
                continue
            if _bbox_intersects(location.bbox, redaction.value_bbox):
                redaction_by_span[location.span_id] = (
                    redaction.label_type,
                    redaction.redaction_id,
                )
                break

    sanitized_locations = []
    for location in result.locations:
        redaction_info = redaction_by_span.get(location.span_id)
        if redaction_info is None:
            sanitized_locations.append(location)
            continue
        redaction_type, redaction_id = redaction_info
        sanitized_locations.append(
            location.model_copy(
                update={
                    "text": REDACTED_TEXT,
                    "is_redacted": True,
                    "redaction_type": redaction_type,
                    "redaction_id": redaction_id,
                }
            )
        )

    redaction_metrics = _build_redaction_metrics(redactions, sanitized_locations)
    return result.model_copy(
        update={
            "text": _rebuild_text(sanitized_locations),
            "locations": sanitized_locations,
            "redactions": redactions,
            "redaction_metrics": redaction_metrics,
        }
    )
