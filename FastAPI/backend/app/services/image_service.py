from pathlib import Path
from shutil import which
from typing import Union

import pytesseract
from PIL import Image, ImageFilter, ImageOps, UnidentifiedImageError

from app.config import get_settings


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
    resized = auto_contrasted.resize(
        (
            max(1, int(width * settings.ocr_upscale_factor)),
            max(1, int(height * settings.ocr_upscale_factor)),
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
    return rotated


def _score_text(text: str) -> tuple[int, int]:
    stripped = text.strip()
    if not stripped:
        return (0, 0)

    useful_chars = sum(char.isalnum() or char.isspace() for char in stripped)
    return (useful_chars, len(stripped))


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


def extract_text_from_image(file_path: Union[str, Path]) -> str:
    image_path = Path(file_path)
    settings = get_settings()
    tesseract_cmd = _resolve_tesseract_cmd()

    if tesseract_cmd is None:
        raise RuntimeError(
            "Tesseract OCR 실행 파일을 찾을 수 없습니다. 서버에 Tesseract를 설치하고 "
            "TESSERACT_CMD 환경변수를 설정해주세요."
        )

    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    try:
        with Image.open(image_path) as image:
            return _ocr_candidates(image, settings.tesseract_lang)
    except UnidentifiedImageError as exc:
        raise ValueError("지원하지 않는 이미지 형식입니다.") from exc
    except pytesseract.TesseractNotFoundError as exc:
        raise RuntimeError(
            "Tesseract OCR이 설치되어 있지 않거나 경로를 찾을 수 없습니다."
        ) from exc
    except pytesseract.TesseractError as exc:
        raise RuntimeError(
            "Tesseract OCR 실행 중 오류가 발생했습니다. 언어 데이터(kor/eng) 설치 여부를 확인해주세요."
        ) from exc
