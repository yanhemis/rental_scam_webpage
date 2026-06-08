from pathlib import Path
from io import BytesIO

import fitz
from PIL import Image

from app.config import get_settings
from app.schemas.extraction_schema import ExtractedTextLocation, ExtractionLocationSource
from app.services.image_service import extract_text_locations_from_pil_image


def extract_text_from_pdf(file_path: str | Path) -> str:
    pdf_path = Path(file_path)
    extracted_pages: list[str] = []

    with fitz.open(pdf_path) as document:
        for page in document:
            extracted_pages.append(page.get_text("text"))

    return "\n".join(part for part in extracted_pages if part).strip()


def extract_text_locations_from_pdf(file_path: str | Path) -> tuple[str, list[ExtractedTextLocation]]:
    settings = get_settings()
    pdf_path = Path(file_path)
    extracted_pages: list[str] = []
    locations: list[ExtractedTextLocation] = []

    with fitz.open(pdf_path) as document:
        for page_index, page in enumerate(document, start=1):
            page_text = page.get_text("text")
            if page_text:
                extracted_pages.append(page_text)

            raw = page.get_text("dict")
            page_locations: list[ExtractedTextLocation] = []
            for block_index, block in enumerate(raw.get("blocks", [])):
                for line_index, line in enumerate(block.get("lines", [])):
                    for span_index, span in enumerate(line.get("spans", [])):
                        text = str(span.get("text") or "").strip()
                        bbox = span.get("bbox")
                        if not text or not bbox:
                            continue
                        page_locations.append(
                            ExtractedTextLocation(
                                span_id=f"p{page_index}-b{block_index}-l{line_index}-s{span_index}",
                                text=text,
                                page_number=page_index,
                                bbox=[float(value) for value in bbox],
                                confidence=None,
                                source=ExtractionLocationSource.pdf_text,
                                coordinate_system="pdf_points",
                            )
                        )
            locations.extend(page_locations)

            if page_text.strip() or page_locations:
                continue

            render_scale = settings.pdf_ocr_render_scale
            pixmap = page.get_pixmap(
                matrix=fitz.Matrix(render_scale, render_scale),
                alpha=False,
            )
            with Image.open(BytesIO(pixmap.tobytes("png"))) as image:
                ocr_text, ocr_locations = extract_text_locations_from_pil_image(
                    image,
                    page_number=page_index,
                    span_prefix="pdf-ocr",
                    coordinate_system=f"pdf_rendered_pixels_{render_scale:g}x",
                )
            if ocr_text:
                extracted_pages.append(ocr_text)
            locations.extend(ocr_locations)

    return "\n".join(part for part in extracted_pages if part).strip(), locations
