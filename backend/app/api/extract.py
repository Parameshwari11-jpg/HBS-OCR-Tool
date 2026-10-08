from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.services.job_service import job_service
from app.services.extraction_service import extraction_service
from app.utils.file_utils import get_job_upload_path
from app.config.languages import get_ocr_lang, DEFAULT_LANGUAGE

router = APIRouter(prefix="/api", tags=["extract"])

class ExtractRequest(BaseModel):
    job_id: str
    language: Optional[str] = DEFAULT_LANGUAGE  # OCR language code from frontend (e.g. 'en', 'fr', 'es')

@router.post("/extract")
async def extract_document(req: ExtractRequest, background_tasks: BackgroundTasks):
    job_status = job_service.get_job_status(req.job_id)
    if not job_status:
        raise HTTPException(status_code=404, detail="Invalid job ID")

    # Resolve the PaddleOCR language string from the user-selected code
    ocr_lang = get_ocr_lang(req.language or DEFAULT_LANGUAGE)

    # Persist the selected language on the job so it can be shown in results
    job_service.set_job_language(req.job_id, ocr_lang)

    upload_path = str(get_job_upload_path(req.job_id, job_status.filename))

    background_tasks.add_task(
        extraction_service.process_document,
        job_id=req.job_id,
        file_path=upload_path,
        filename=job_status.filename,
        file_type=job_status.file_type,
        language=ocr_lang
    )

    return {
        "job_id": req.job_id,
        "status": "processing",
        "language": ocr_lang
    }
