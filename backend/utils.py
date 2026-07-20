"""Small shared helpers: file-upload validation/storage."""
import os
import uuid
from fastapi import UploadFile

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "pdf", "docx", "txt", "log", "zip"}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB

os.makedirs(UPLOAD_DIR, exist_ok=True)


def is_allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_upload(file: UploadFile) -> tuple[str, str]:
    """Saves an UploadFile under a random name; returns (stored_name, original_name)."""
    ext = file.filename.rsplit(".", 1)[1].lower()
    stored_name = f"{uuid.uuid4().hex}.{ext}"
    destination = os.path.join(UPLOAD_DIR, stored_name)

    contents = file.file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise ValueError("File exceeds the 5 MB upload limit.")

    with open(destination, "wb") as out_file:
        out_file.write(contents)

    return stored_name, file.filename
