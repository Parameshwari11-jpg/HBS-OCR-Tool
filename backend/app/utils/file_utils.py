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

def cleanup_old_sessions(max_keep: int = 2):
    """
    Automatically keeps only the latest `max_keep` session directories in `temp`
    and uploaded files in `uploads`, removing all older sessions.
    """
    try:
        # 1. Clean TEMP_DIR session folders
        if TEMP_DIR.exists():
            session_dirs = []
            for d in TEMP_DIR.iterdir():
                if d.is_dir():
                    try:
                        session_dirs.append((d.stat().st_mtime, d))
                    except Exception:
                        pass
            
            # Sort by modification time: oldest first
            session_dirs.sort(key=lambda x: x[0])
            
            if len(session_dirs) > max_keep:
                to_delete = session_dirs[:-max_keep]
                for _, d in to_delete:
                    # Delete temp directory for this session
                    shutil.rmtree(d, ignore_errors=True)
                    # Delete corresponding file in uploads directory if present
                    job_id = d.name
                    for ext in [".pdf", ".docx", ".png", ".jpg", ".jpeg"]:
                        up_file = UPLOAD_DIR / f"{job_id}{ext}"
                        if up_file.exists():
                            try:
                                up_file.unlink()
                            except Exception:
                                pass

        # 2. Clean standalone files in UPLOAD_DIR
        if UPLOAD_DIR.exists():
            upload_files = []
            for f in UPLOAD_DIR.iterdir():
                if f.is_file() and not f.name.startswith("~$"):
                    try:
                        upload_files.append((f.stat().st_mtime, f))
                    except Exception:
                        pass
            
            upload_files.sort(key=lambda x: x[0])
            if len(upload_files) > max_keep:
                to_delete_files = upload_files[:-max_keep]
                for _, f in to_delete_files:
                    try:
                        f.unlink()
                    except Exception:
                        pass
    except Exception as e:
        import logging
        logging.getLogger("file_utils").warning(f"Error during cleanup_old_sessions: {e}")

def get_job_temp_dir(job_id: str) -> Path:
    cleanup_old_sessions(max_keep=2)
    job_temp = TEMP_DIR / job_id
    os.makedirs(job_temp, exist_ok=True)
    return job_temp

def cleanup_job_temp(job_id: str):
    job_temp = TEMP_DIR / job_id
    if job_temp.exists():
        shutil.rmtree(job_temp, ignore_errors=True)

