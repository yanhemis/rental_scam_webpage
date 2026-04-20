from pathlib import Path

import fitz


def extract_text_from_pdf(file_path: str | Path) -> str:
    pdf_path = Path(file_path)
    extracted_pages: list[str] = []

    with fitz.open(pdf_path) as document:
        for page in document:
            extracted_pages.append(page.get_text("text"))

    return "\n".join(part for part in extracted_pages if part).strip()
