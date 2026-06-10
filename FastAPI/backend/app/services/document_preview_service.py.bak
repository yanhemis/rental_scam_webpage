from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path

import fitz
from PIL import Image, ImageOps, UnidentifiedImageError

from app.config import get_settings
from app.schemas.document_schema import DocumentPreviewPage


def _image_to_data_url(image: Image.Image) -> str:
    settings = get_settings()
    output = BytesIO()
    image.convert("RGB").save(
        output,
        format="JPEG",
        quality=settings.document_preview_jpeg_quality,
        optimize=True,
    )
    encoded = base64.b64encode(output.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def _preview_coordinate_system_for_pdf() -> str:
    settings = get_settings()
    scale = settings.pdf_ocr_render_scale
    if settings.local_ocr_provider == "easyocr":
        return f"easyocr_pdf_rendered_pixels_{scale:g}x"
    if settings.local_ocr_provider == "paddleocr":
        return f"paddleocr_pdf_rendered_pixels_{scale:g}x"
    return f"pdf_rendered_pixels_{scale:g}x"


def build_document_preview_pages(
    file_path: str | Path,
    content_type: str | None,
) -> list[DocumentPreviewPage]:
    settings = get_settings()
    path = Path(file_path)
    normalized_content_type = (content_type or "").lower()

    if normalized_content_type == "application/pdf":
        return _build_pdf_preview_pages(path)
    if normalized_content_type.startswith("image/"):
        return _build_image_preview_page(path)
    return []


def _build_pdf_preview_pages(pdf_path: Path) -> list[DocumentPreviewPage]:
    settings = get_settings()
    pages: list[DocumentPreviewPage] = []
    scale = settings.pdf_ocr_render_scale

    with fitz.open(pdf_path) as document:
        max_pages = min(len(document), settings.document_preview_max_pages)
        for page_index in range(max_pages):
            page = document[page_index]
            pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            with Image.open(BytesIO(pixmap.tobytes("png"))) as image:
                rendered = image.convert("RGB")
                pages.append(
                    DocumentPreviewPage(
                        page_number=page_index + 1,
                        width=rendered.width,
                        height=rendered.height,
                        image_data_url=_image_to_data_url(rendered),
                        coordinate_system=_preview_coordinate_system_for_pdf(),
                    )
                )

    return pages


def _build_image_preview_page(image_path: Path) -> list[DocumentPreviewPage]:
    try:
        with Image.open(image_path) as image:
            rendered = ImageOps.exif_transpose(image).convert("RGB")
            coordinate_system = (
                "easyocr_image_pixels"
                if get_settings().local_ocr_provider == "easyocr"
                else "paddleocr_image_pixels"
                if get_settings().local_ocr_provider == "paddleocr"
                else "source_image_pixels"
            )
            return [
                DocumentPreviewPage(
                    page_number=1,
                    width=rendered.width,
                    height=rendered.height,
                    image_data_url=_image_to_data_url(rendered),
                    coordinate_system=coordinate_system,
                )
            ]
    except UnidentifiedImageError:
        return []
