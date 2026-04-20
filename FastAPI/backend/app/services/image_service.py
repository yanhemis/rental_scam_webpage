from pathlib import Path

import pytesseract
from PIL import Image, UnidentifiedImageError


def extract_text_from_image(file_path: str | Path) -> str:
    image_path = Path(file_path)

    try:
        with Image.open(image_path) as image:
            return pytesseract.image_to_string(image, lang="kor+eng").strip()
    except UnidentifiedImageError as exc:
        raise ValueError("지원하지 않는 이미지 형식입니다.") from exc
    except pytesseract.TesseractNotFoundError as exc:
        raise RuntimeError("Tesseract OCR이 설치되어 있지 않습니다.") from exc
