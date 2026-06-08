from __future__ import annotations

import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
VENV_SITE_PACKAGES = Path(r"C:\Users\USER\Desktop\FastAPI\backend\venv\Lib\site-packages")

if str(VENV_SITE_PACKAGES) not in sys.path:
    sys.path.insert(0, str(VENV_SITE_PACKAGES))

import fitz  # type: ignore


PAGE_WIDTH = 595
PAGE_HEIGHT = 842
CONTENT_RECT = fitz.Rect(24, 24, 571, 818)


def render_html_file(html_path: Path) -> Path:
    html = html_path.read_text(encoding="utf-8")
    doc = fitz.open()
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    page.insert_htmlbox(CONTENT_RECT, html)
    png_path = html_path.with_suffix(".png")
    pix = page.get_pixmap(dpi=170, alpha=False)
    pix.save(png_path)
    return png_path


def main() -> None:
    html_files = sorted(BASE_DIR.glob("sample_*_standard_form*.html"))
    if not html_files:
        raise SystemExit("No sample HTML files found.")

    rendered = [render_html_file(path) for path in html_files]
    for path in rendered:
        print(path)


if __name__ == "__main__":
    main()
