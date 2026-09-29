from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from app.services.job_service import job_service
from app.services.extraction_service import extraction_service
from app.utils.file_utils import get_job_upload_path

router = APIRouter(prefix="/api", tags=["extract"])

class ExtractRequest(BaseModel):
    job_id: str

@router.post("/extract")
async def extract_document(req: ExtractRequest, background_tasks: BackgroundTasks):
    job_status = job_service.get_job_status(req.job_id)
    if not job_status:
        raise HTTPException(status_code=404, detail="Invalid job ID")

    upload_path = str(get_job_upload_path(req.job_id, job_status.filename))

    background_tasks.add_task(
        extraction_service.process_document,
        job_id=req.job_id,
        file_path=upload_path,
        filename=job_status.filename,
        file_type=job_status.file_type
    )

    return {
        "job_id": req.job_id,
        "status": "processing"
    }
