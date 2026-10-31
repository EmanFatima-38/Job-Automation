import uuid
from pathlib import Path

from fastapi import UploadFile

from app.config import get_settings

settings = get_settings()


def save_upload_file(upload_file: UploadFile) -> str:
    storage_dir = Path(settings.file_storage_dir)
    storage_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(upload_file.filename or "").suffix
    dest_path = storage_dir / f"{uuid.uuid4()}{suffix}"

    with dest_path.open("wb") as f:
        f.write(upload_file.file.read())

    return str(dest_path)
