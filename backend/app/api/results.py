import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from app.services.job_service import job_service
from app.utils.file_utils import get_job_temp_dir

router = APIRouter(prefix="/api", tags=["results"])

@router.get("/status/{job_id}")
async def get_status(job_id: str):
    job_status = job_service.get_job_status(job_id)
    if not job_status:
        raise HTTPException(status_code=404, detail="Job ID not found")
    return job_status

@router.get("/results/lookup")
async def lookup_results(filename: str = ""):
    result = job_service.find_latest_result(filename=filename if filename else None)
    if not result:
        raise HTTPException(status_code=404, detail="No matching extraction result found")
    return result

@router.get("/results/{job_id}")
async def get_results(job_id: str):
    result = job_service.get_result(job_id)
    if not result:
        job_status = job_service.get_job_status(job_id)
        if job_status and job_status.status == "processing":
            raise HTTPException(status_code=202, detail="Job is still processing")
        raise HTTPException(status_code=404, detail="Results not found for job ID")
    return result

@router.get("/preview/{job_id}/{page_num}")
async def get_page_preview(job_id: str, page_num: int):
    temp_dir = get_job_temp_dir(job_id)
    page_img_path = temp_dir / f"page_{page_num}.png"
    if not page_img_path.exists():
        raise HTTPException(status_code=404, detail=f"Page preview for page {page_num} not found")
    return FileResponse(path=page_img_path, media_type="image/png")

@router.get("/image/{job_id}/{image_filename}")
async def get_extracted_image(job_id: str, image_filename: str):
    temp_dir = get_job_temp_dir(job_id)
    img_path = temp_dir / image_filename
    if not img_path.exists():
        raise HTTPException(status_code=404, detail=f"Image {image_filename} not found")
    
    ext = img_path.suffix.lower()
    media_type = "image/png"
    if ext in (".jpg", ".jpeg"):
        media_type = "image/jpeg"
    elif ext == ".webp":
        media_type = "image/webp"
    elif ext == ".gif":
        media_type = "image/gif"
        
    return FileResponse(path=img_path, media_type=media_type)
