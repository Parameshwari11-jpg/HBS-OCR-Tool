import shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.utils.file_utils import validate_file_extension, generate_job_id, get_job_upload_path
from app.services.job_service import job_service

router = APIRouter(prefix="/api", tags=["upload"])

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    filename = file.filename or "document"
    if not validate_file_extension(filename):
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Please upload a PDF or DOCX file."
        )

    job_id = generate_job_id()
    ext = Path(filename).suffix.lower().replace(".", "")
    dest_path = get_job_upload_path(job_id, filename)

    try:
        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {str(e)}")

    job_service.create_job(job_id, filename, ext)

    return {
        "job_id": job_id,
        "filename": filename,
        "status": "uploaded"
    }
