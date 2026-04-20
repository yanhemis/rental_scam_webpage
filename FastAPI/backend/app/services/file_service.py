from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.config import get_settings
from typing import Optional


def _safe_filename(filename: Optional[str]) -> str:
    original_name = Path(filename or "upload.bin").name
    suffix = Path(original_name).suffix.lower()
    stem = Path(original_name).stem or "upload"
    sanitized_stem = "".join(
        char if char.isalnum() or char in {"-", "_"} else "_"
        for char in stem
    ).strip("_") or "upload"
    return f"{sanitized_stem}_{uuid4().hex}{suffix}"


async def save_upload_file(file: UploadFile) -> tuple[Path, str]:
    settings = get_settings()
    contents = await file.read()
    file_hash = sha256(contents).hexdigest()

    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    saved_path = settings.upload_dir / _safe_filename(file.filename)
    saved_path.write_bytes(contents)

    await file.seek(0)
    return saved_path, file_hash