from __future__ import annotations

import argparse
import time
from io import BytesIO
from pathlib import Path

import fitz
import numpy as np
from PIL import Image


def render_pdf_page(pdf_path: Path, page_number: int, scale: float) -> Image.Image:
    with fitz.open(pdf_path) as document:
        page = document[page_number - 1]
        pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
    return Image.open(BytesIO(pixmap.tobytes("png"))).convert("RGB")


def score_text(text: str) -> dict[str, float | int]:
    compact = "".join(text.split())
    hangul = sum("가" <= char <= "힣" for char in compact)
    digits = sum(char.isdigit() for char in compact)
    return {
        "length": len(text),
        "compact_length": len(compact),
        "hangul": hangul,
        "digits": digits,
        "hangul_ratio": round(hangul / max(1, len(compact)), 3),
    }


def run_easyocr(pdf_path: Path, pages: list[int], scale: float, gpu: bool) -> None:
    import easyocr

    started = time.perf_counter()
    reader = easyocr.Reader(["ko", "en"], gpu=gpu, verbose=False)
    print(f"engine=easyocr init_seconds={time.perf_counter() - started:.2f}")

    for page_number in pages:
        image = render_pdf_page(pdf_path, page_number, scale)
        started = time.perf_counter()
        results = reader.readtext(np.array(image), detail=1, paragraph=False)
        seconds = time.perf_counter() - started
        words = [str(item[1]).strip() for item in results if str(item[1]).strip()]
        text = " ".join(words)
        metrics = score_text(text)
        print(
            f"page={page_number} seconds={seconds:.2f} boxes={len(results)} "
            f"length={metrics['length']} hangul={metrics['hangul']} "
            f"hangul_ratio={metrics['hangul_ratio']}"
        )
        print(text[:700].replace("\n", " "))
        print("---")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf_path", type=Path)
    parser.add_argument("--pages", default="2,3")
    parser.add_argument("--scale", type=float, default=2.0)
    parser.add_argument("--gpu", action="store_true")
    args = parser.parse_args()

    pages = [int(value.strip()) for value in args.pages.split(",") if value.strip()]
    run_easyocr(args.pdf_path, pages, args.scale, args.gpu)


if __name__ == "__main__":
    main()
