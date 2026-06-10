from __future__ import annotations

import argparse
import os
import time
from io import BytesIO
from pathlib import Path
from typing import Union

import fitz
import numpy as np
from PIL import Image


def render_pdf_page(pdf_path: Path, page_number: int, scale: float) -> Image.Image:
    with fitz.open(pdf_path) as document:
        page = document[page_number - 1]
        pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
    return Image.open(BytesIO(pixmap.tobytes("png"))).convert("RGB")


def score_text(text: str) -> dict[str, Union[float, int]]:
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


def run_paddleocr(pdf_path: Path, pages: list[int], scale: float) -> None:
    os.environ.setdefault("FLAGS_use_mkldnn", "0")
    os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
    try:
        from paddleocr import PaddleOCR
    except ImportError as exc:
        print(f"engine=paddleocr unavailable import_error={exc}")
        return

    started = time.perf_counter()
    try:
        ocr = PaddleOCR(lang="korean")
    except Exception as exc:
        print(f"engine=paddleocr init_failed seconds={time.perf_counter() - started:.2f}")
        print(f"reason={type(exc).__name__}: {exc}")
        return
    print(f"engine=paddleocr init_seconds={time.perf_counter() - started:.2f}")

    for page_number in pages:
        image = render_pdf_page(pdf_path, page_number, scale)
        started = time.perf_counter()
        try:
            if hasattr(ocr, "predict"):
                results = ocr.predict(np.array(image))
            else:
                results = ocr.ocr(np.array(image))
        except Exception as exc:
            print(f"page={page_number} failed={type(exc).__name__}: {exc}")
            continue
        seconds = time.perf_counter() - started
        words = _paddle_words(results)
        text = " ".join(words)
        metrics = score_text(text)
        print(
            f"page={page_number} seconds={seconds:.2f} boxes={len(words)} "
            f"length={metrics['length']} hangul={metrics['hangul']} "
            f"hangul_ratio={metrics['hangul_ratio']}"
        )
        print(text[:700].replace("\n", " "))
        print("---")


def _paddle_words(results) -> list[str]:
    words: list[str] = []
    if not results:
        return words
    for page_result in results:
        if isinstance(page_result, dict):
            rec_texts = page_result.get("rec_texts") or []
            words.extend(str(value).strip() for value in rec_texts if str(value).strip())
            continue
        for item in page_result or []:
            if isinstance(item, dict):
                text = item.get("text") or item.get("rec_text")
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                payload = item[1]
                text = payload[0] if isinstance(payload, (list, tuple)) and payload else payload
            else:
                text = None
            if text:
                words.append(str(text).strip())
    return [word for word in words if word]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf_path", type=Path)
    parser.add_argument("--pages", default="2,3")
    parser.add_argument("--scale", type=float, default=2.0)
    parser.add_argument("--engine", choices=("easyocr", "paddleocr", "both"), default="easyocr")
    parser.add_argument("--gpu", action="store_true")
    args = parser.parse_args()

    pages = [int(value.strip()) for value in args.pages.split(",") if value.strip()]
    if args.engine in {"easyocr", "both"}:
        run_easyocr(args.pdf_path, pages, args.scale, args.gpu)
    if args.engine in {"paddleocr", "both"}:
        run_paddleocr(args.pdf_path, pages, args.scale)


if __name__ == "__main__":
    main()
