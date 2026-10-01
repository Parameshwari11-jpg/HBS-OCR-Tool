import os
import shutil
import uuid
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
TEMP_DIR = BASE_DIR / "temp"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".docx"}

def validate_file_extension(filename: str) -> bool:
    ext = Path(filename).suffix.lower()
    return ext in ALLOWED_EXTENSIONS

def generate_job_id() -> str:
    return str(uuid.uuid4())

def get_upload_dir() -> Path:
    return UPLOAD_DIR

def get_job_upload_path(job_id: str, original_filename: str) -> Path:
    ext = Path(original_filename).suffix.lower()
    return UPLOAD_DIR / f"{job_id}{ext}"

def get_job_temp_dir(job_id: str) -> Path:
    job_temp = TEMP_DIR / job_id
    os.makedirs(job_temp, exist_ok=True)
    return job_temp

def cleanup_job_temp(job_id: str):
    job_temp = TEMP_DIR / job_id
    if job_temp.exists():
        shutil.rmtree(job_temp, ignore_errors=True)
