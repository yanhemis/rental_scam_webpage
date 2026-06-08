from pathlib import Path
from shutil import which

import pytesseract
from PIL import Image, ImageFilter, ImageOps, UnidentifiedImageError

from app.config import get_settings
from app.schemas.extraction_schema import ExtractedTextLocation, ExtractionLocationSource

_easyocr_reader = None


def _resolve_tesseract_cmd() -> str | None:
    settings = get_settings()

    if settings.tesseract_cmd:
        return settings.tesseract_cmd

    discovered = which("tesseract")
    if discovered:
        return discovered

    candidates = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        "/usr/bin/tesseract",
        "/usr/local/bin/tesseract",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate

    return None


def _trim_borders(image: Image.Image) -> Image.Image:
    settings = get_settings()
    width, height = image.size
    crop_x = int(width * settings.ocr_crop_border_ratio)
    crop_y = int(height * settings.ocr_crop_border_ratio)

    if crop_x == 0 and crop_y == 0:
        return image

    left = min(crop_x, width // 10)
    top = min(crop_y, height // 10)
    right = max(left + 1, width - left)
    bottom = max(top + 1, height - top)
    return image.crop((left, top, right, bottom))


def _normalize_image(image: Image.Image) -> Image.Image:
    settings = get_settings()
    transposed = ImageOps.exif_transpose(image)
    trimmed = _trim_borders(transposed)
    grayscale = ImageOps.grayscale(trimmed)
    denoised = grayscale.filter(ImageFilter.MedianFilter(size=3))
    auto_contrasted = ImageOps.autocontrast(denoised)
    width, height = auto_contrasted.size
    upscale_factor = settings.ocr_upscale_factor
    if max(width, height) >= 2200:
        upscale_factor = 1.0
    resized = auto_contrasted.resize(
        (
            max(1, int(width * upscale_factor)),
            max(1, int(height * upscale_factor)),
        )
    )
    sharpened = resized.filter(ImageFilter.SHARPEN)
    return sharpened


def _threshold_image(image: Image.Image, threshold_bias: int) -> Image.Image:
    return image.point(lambda px: 255 if px > threshold_bias else 0)


def _rotated_candidates(image: Image.Image) -> list[Image.Image]:
    settings = get_settings()
    candidates: list[Image.Image] = []

    for angle in settings.ocr_rotation_angles:
        if angle == 0:
            candidates.append(image)
            continue
        candidates.append(image.rotate(angle, expand=True, fillcolor=255))

    return candidates


def _candidate_images(image: Image.Image) -> list[Image.Image]:
    settings = get_settings()
    normalized = _normalize_image(image)
    variants = [
        normalized,
        _threshold_image(normalized, settings.ocr_threshold_bias),
        _threshold_image(normalized, max(120, settings.ocr_threshold_bias - 20)),
        ImageOps.invert(_threshold_image(normalized, settings.ocr_threshold_bias)),
    ]

    rotated: list[Image.Image] = []
    for variant in variants:
        rotated.extend(_rotated_candidates(variant))
    return rotated[: settings.ocr_max_candidate_images]


def _score_text(text: str) -> tuple[int, int]:
    stripped = text.strip()
    if not stripped:
        return (0, 0)

    hangul_count = sum("가" <= char <= "힣" for char in stripped)
    digit_count = sum(char.isdigit() for char in stripped)
    latin_count = sum(char.isascii() and char.isalpha() for char in stripped)
    contract_terms = (
        "계약",
        "임대",
        "임차",
        "보증금",
        "차임",
        "전세",
        "월세",
        "확정일자",
        "전입신고",
        "특약",
        "주소",
        "소유자",
    )
    term_hits = sum(1 for term in contract_terms if term in stripped)
    useful_score = hangul_count * 5 + digit_count * 2 + term_hits * 60
    noise_penalty = latin_count if hangul_count < 5 else latin_count // 4
    return (useful_score - noise_penalty, len(stripped))


def _extract_locations_from_tesseract_data(
    data: dict,
    *,
    page_number: int,
    span_prefix: str,
    source: ExtractionLocationSource,
    coordinate_system: str,
) -> list[ExtractedTextLocation]:
    locations: list[ExtractedTextLocation] = []
    for index, text in enumerate(data.get("text", [])):
        word = str(text or "").strip()
        if not word:
            continue

        try:
            raw_confidence = float(data["conf"][index])
            confidence = raw_confidence / 100 if raw_confidence >= 0 else None
        except (KeyError, TypeError, ValueError):
            confidence = None

        left = float(data["left"][index])
        top = float(data["top"][index])
        width = float(data["width"][index])
        height = float(data["height"][index])
        locations.append(
            ExtractedTextLocation(
                span_id=f"{span_prefix}-p{page_number}-w{index}",
                text=word,
                page_number=page_number,
                bbox=[left, top, left + width, top + height],
                confidence=confidence,
                source=source,
                coordinate_system=coordinate_system,
            )
        )

    return locations


def _get_easyocr_reader():
    global _easyocr_reader
    if _easyocr_reader is None:
        try:
            import easyocr
        except ImportError as exc:
            raise RuntimeError(
                "EasyOCR is not installed. Install backend/requirements-ocr-local.txt "
                "or set LOCAL_OCR_PROVIDER=tesseract."
            ) from exc
        _easyocr_reader = easyocr.Reader(["ko", "en"], gpu=False, verbose=False)
    return _easyocr_reader


def _extract_locations_from_easyocr_results(
    results: list,
    *,
    page_number: int,
    span_prefix: str,
    source: ExtractionLocationSource,
    coordinate_system: str,
) -> list[ExtractedTextLocation]:
    locations: list[ExtractedTextLocation] = []
    for index, item in enumerate(results):
        if len(item) < 2:
            continue

        points = item[0]
        word = str(item[1] or "").strip()
        if not word or not points:
            continue

        try:
            confidence = float(item[2]) if len(item) >= 3 else None
        except (TypeError, ValueError):
            confidence = None

        xs = [float(point[0]) for point in points]
        ys = [float(point[1]) for point in points]
        locations.append(
            ExtractedTextLocation(
                span_id=f"{span_prefix}-p{page_number}-e{index}",
                text=word,
                page_number=page_number,
                bbox=[min(xs), min(ys), max(xs), max(ys)],
                confidence=confidence,
                source=source,
                coordinate_system=coordinate_system,
            )
        )

    return locations


def _ocr_easyocr_image(
    image: Image.Image,
    *,
    page_number: int,
    span_prefix: str,
    coordinate_system: str,
) -> tuple[str, list[ExtractedTextLocation]]:
    try:
        import numpy as np
    except ImportError as exc:
        raise RuntimeError(
            "NumPy is required for EasyOCR. Install backend/requirements-ocr-local.txt."
        ) from exc

    reader = _get_easyocr_reader()
    normalized = ImageOps.exif_transpose(image).convert("RGB")
    results = reader.readtext(np.array(normalized), detail=1, paragraph=False)
    locations = _extract_locations_from_easyocr_results(
        results,
        page_number=page_number,
        span_prefix=span_prefix,
        source=ExtractionLocationSource.image_ocr,
        coordinate_system=coordinate_system,
    )
    text = " ".join(location.text for location in locations)
    return text, locations


def _ocr_data_candidates(
    image: Image.Image,
    lang: str,
) -> tuple[str, dict | None, str]:
    settings = get_settings()
    best_text = ""
    best_candidate: Image.Image | None = None
    best_psm_mode = settings.tesseract_psm_modes[0] if settings.tesseract_psm_modes else 6
    best_coordinate_system = "normalized_image_pixels"
    best_score = (0, 0)

    for variant_index, candidate in enumerate(_candidate_images(image)):
        for psm_mode in settings.tesseract_psm_modes:
            text = pytesseract.image_to_string(
                candidate,
                lang=lang,
                config=f"--oem 3 --psm {psm_mode}",
            ).strip()
            score = _score_text(text)
            if score > best_score:
                best_score = score
                best_text = text
                best_candidate = candidate
                best_psm_mode = psm_mode
                best_coordinate_system = f"ocr_candidate_{variant_index}_psm_{psm_mode}_pixels"

    if best_candidate is None:
        return best_text, None, best_coordinate_system

    best_data = pytesseract.image_to_data(
        best_candidate,
        lang=lang,
        config=f"--oem 3 --psm {best_psm_mode}",
        output_type=pytesseract.Output.DICT,
    )
    return best_text, best_data, best_coordinate_system


def _ocr_candidates(image: Image.Image, lang: str) -> str:
    settings = get_settings()
    best_text = ""
    best_score = (0, 0)

    for candidate in _candidate_images(image):
        for psm_mode in settings.tesseract_psm_modes:
            text = pytesseract.image_to_string(
                candidate,
                lang=lang,
                config=f"--oem 3 --psm {psm_mode}",
            ).strip()
            score = _score_text(text)
            if score > best_score:
                best_score = score
                best_text = text

    return best_text


def _ensure_tesseract_cmd() -> None:
    tesseract_cmd = _resolve_tesseract_cmd()
    if tesseract_cmd is None:
        raise RuntimeError(
            "Tesseract OCR executable was not found. Install Tesseract or set TESSERACT_CMD."
        )
    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd


def extract_text_from_image(file_path: str | Path) -> str:
    image_path = Path(file_path)
    settings = get_settings()

    try:
        with Image.open(image_path) as image:
            if settings.local_ocr_provider == "easyocr":
                text, _locations = _ocr_easyocr_image(
                    image,
                    page_number=1,
                    span_prefix="img",
                    coordinate_system="easyocr_image_pixels",
                )
                return text

            _ensure_tesseract_cmd()
            return _ocr_candidates(image, settings.tesseract_lang)
    except UnidentifiedImageError as exc:
        raise ValueError("Unsupported image format.") from exc
    except pytesseract.TesseractNotFoundError as exc:
        raise RuntimeError("Tesseract OCR is not installed or cannot be found.") from exc
    except pytesseract.TesseractError as exc:
        raise RuntimeError("Tesseract OCR failed while extracting image text.") from exc


def extract_text_locations_from_image(
    file_path: str | Path,
) -> tuple[str, list[ExtractedTextLocation]]:
    image_path = Path(file_path)
    settings = get_settings()

    try:
        with Image.open(image_path) as image:
            if settings.local_ocr_provider == "easyocr":
                return _ocr_easyocr_image(
                    image,
                    page_number=1,
                    span_prefix="img",
                    coordinate_system="easyocr_image_pixels",
                )

            _ensure_tesseract_cmd()
            best_text, data, coordinate_system = _ocr_data_candidates(
                image,
                settings.tesseract_lang,
            )
    except UnidentifiedImageError as exc:
        raise ValueError("Unsupported image format.") from exc
    except pytesseract.TesseractNotFoundError as exc:
        raise RuntimeError("Tesseract OCR is not installed or cannot be found.") from exc
    except pytesseract.TesseractError as exc:
        raise RuntimeError("Tesseract OCR failed while collecting text locations.") from exc

    locations = _extract_locations_from_tesseract_data(
        data or {},
        page_number=1,
        span_prefix="img",
        source=ExtractionLocationSource.image_ocr,
        coordinate_system=coordinate_system,
    )
    return best_text, locations


def extract_text_locations_from_pil_image(
    image: Image.Image,
    *,
    page_number: int = 1,
    span_prefix: str = "img",
    coordinate_system: str = "normalized_image_pixels",
) -> tuple[str, list[ExtractedTextLocation]]:
    settings = get_settings()

    if settings.local_ocr_provider == "easyocr":
        return _ocr_easyocr_image(
            image,
            page_number=page_number,
            span_prefix=span_prefix,
            coordinate_system=f"easyocr_{coordinate_system}",
        )

    _ensure_tesseract_cmd()

    try:
        best_text, data, selected_coordinate_system = _ocr_data_candidates(
            image,
            settings.tesseract_lang,
        )
    except pytesseract.TesseractNotFoundError as exc:
        raise RuntimeError("Tesseract OCR is not installed or cannot be found.") from exc
    except pytesseract.TesseractError as exc:
        raise RuntimeError("Tesseract OCR failed while collecting text locations.") from exc

    locations = _extract_locations_from_tesseract_data(
        data or {},
        page_number=page_number,
        span_prefix=span_prefix,
        source=ExtractionLocationSource.image_ocr,
        coordinate_system=selected_coordinate_system or coordinate_system,
    )
    return best_text, locations
