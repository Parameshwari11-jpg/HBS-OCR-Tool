import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response, JSONResponse
from app.services.job_service import job_service

router = APIRouter(prefix="/api/export", tags=["export"])

@router.get("/{job_id}/txt")
async def export_txt(job_id: str):
    result = job_service.get_result(job_id)
    if not result:
        raise HTTPException(status_code=404, detail="Results not found for job ID")

    filename_base = result.filename.rsplit('.', 1)[0]
    export_filename = f"{filename_base}_extracted.txt"

    return Response(
        content=result.reconstructed_text,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{export_filename}"'}
    )

@router.get("/{job_id}/json")
async def export_json(job_id: str):
    result = job_service.get_result(job_id)
    if not result:
        raise HTTPException(status_code=404, detail="Results not found for job ID")

    filename_base = result.filename.rsplit('.', 1)[0]
    export_filename = f"{filename_base}_extracted.json"

    json_data = result.model_dump()

    return Response(
        content=json.dumps(json_data, indent=2, ensure_ascii=False),
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{export_filename}"'}
    )
