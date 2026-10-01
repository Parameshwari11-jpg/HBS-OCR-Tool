import os
import shutil
import tempfile
import pymupdf
import docx
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Response
from fastapi.responses import FileResponse, PlainTextResponse

from app.originality.comparator import originality_comparator
from app.originality.report_generator import ReportGenerator
from app.originality.models import OriginalityReport, DocumentMetadata
from app.services.job_service import job_service
from app.utils.file_utils import get_upload_dir, get_job_temp_dir

router = APIRouter(prefix="/api/originality", tags=["originality"])


@router.post("/metadata")
async def inspect_document_metadata(
    file: UploadFile = File(...)
):
    """
    Extracts high-level document statistics (pages, word count, character count)
    for UI preview before starting comparison.
    """
    fn = file.filename or "uploaded_file"
    ext = os.path.splitext(fn)[1].lower()

    if ext not in (".pdf", ".docx", ".doc"):
        raise HTTPException(status_code=400, detail=f"Unsupported format: {ext}. Only PDF and Word (.docx) are supported.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp_path = tmp.name
        content = await file.read()
        tmp.write(content)

    try:
        if ext == ".pdf":
            doc = pymupdf.open(tmp_path)
            total_pages = len(doc)
            all_text = "".join([doc[i].get_text() for i in range(min(5, total_pages))])
            doc.close()
            return DocumentMetadata(
                filename=fn,
                file_type="pdf",
                total_pages=total_pages,
                word_count=len(all_text.split()),
                character_count=len(all_text)
            )
        else:
            doc = docx.Document(tmp_path)
            paras = doc.paragraphs
            all_text = " ".join([p.text for p in paras])
            return DocumentMetadata(
                filename=fn,
                file_type="docx",
                total_sections=len(paras),
                word_count=len(all_text.split()),
                character_count=len(all_text)
            )
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@router.post("/check", response_model=OriginalityReport)
async def check_originality(
    original_file: Optional[UploadFile] = File(None),
    extracted_file: Optional[UploadFile] = File(None),
    job_id: Optional[str] = Form(None),
    extracted_text: Optional[str] = Form(None),
    original_filename: Optional[str] = Form(None),
    extracted_filename: Optional[str] = Form(None)
):
    """
    Runs originality and extraction accuracy verification.
    Accepts either directly uploaded files, or references an existing extraction job_id.
    """
    temp_dir = tempfile.mkdtemp(prefix="orig_check_")
    orig_path: Optional[str] = None
    orig_name: str = original_filename or "original_document"
    ext_name: str = extracted_filename or "extracted_text.txt"
    text_content: str = extracted_text or ""

    try:
        # 1. Resolve Original Document Path
        if original_file and original_file.filename:
            orig_name = original_file.filename
            ext = os.path.splitext(orig_name)[1].lower()
            orig_path = os.path.join(temp_dir, f"original{ext}")
            with open(orig_path, "wb") as f:
                f.write(await original_file.read())
        elif job_id:
            # Look up uploaded file from existing job
            upload_dir = get_upload_dir()
            # Find matching file in upload_dir
            for f in os.listdir(upload_dir):
                if f.startswith(job_id):
                    orig_path = os.path.join(upload_dir, f)
                    job_res = job_service.get_result(job_id)
                    if job_res:
                        orig_name = job_res.filename
                    break

            if not orig_path or not os.path.exists(orig_path):
                raise HTTPException(status_code=404, detail=f"Original document not found for job ID: {job_id}")
        else:
            raise HTTPException(status_code=400, detail="Either an original file or a valid job_id must be provided.")

        # 2. Resolve Extracted Text
        if extracted_file and extracted_file.filename:
            ext_name = extracted_file.filename
            file_bytes = await extracted_file.read()
            text_content = file_bytes.decode("utf-8", errors="replace")
        elif not text_content and job_id:
            # Fetch reconstructed_text from existing job result
            job_res = job_service.get_result(job_id)
            if job_res and job_res.reconstructed_text:
                text_content = job_res.reconstructed_text
                ext_name = f"{os.path.splitext(job_res.filename)[0]}.txt"

        if not text_content:
            raise HTTPException(status_code=400, detail="Extracted text is empty or missing. Please upload a .txt file or provide text.")

        # 3. Execute Originality & Accuracy Comparison
        report = originality_comparator.compare(
            original_file_path=orig_path,
            extracted_text=text_content,
            original_filename=orig_name,
            extracted_filename=ext_name,
            job_id=job_id
        )

        return report

    finally:
        # Clean up temporary upload directory if created
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


@router.get("/preview/{report_id}/{page_num}")
async def get_originality_page_preview(report_id: str, page_num: int):
    """
    Returns visual document page preview image for side-by-side originality inspection.
    """
    # 1. Check report-specific temp directory
    report_temp = get_job_temp_dir(report_id)
    page_img_path = report_temp / f"page_{page_num}.png"
    if page_img_path.exists():
        return FileResponse(path=page_img_path, media_type="image/png")

    # 2. Check if linked to an extraction job_id
    report = originality_comparator.get_report(report_id)
    if report and report.job_id:
        job_temp = get_job_temp_dir(report.job_id)
        job_page_img = job_temp / f"page_{page_num}.png"
        if job_page_img.exists():
            return FileResponse(path=job_page_img, media_type="image/png")

    raise HTTPException(status_code=404, detail=f"Page preview for page {page_num} not found")


@router.get("/report/{report_id}", response_model=OriginalityReport)
async def get_report(report_id: str):
    """
    Returns full originality verification report by ID.
    """
    report = originality_comparator.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report ID not found")
    return report


@router.get("/report/{report_id}/json")
async def export_json(report_id: str):
    """
    Downloads originality report as machine-readable JSON.
    """
    report = originality_comparator.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report ID not found")

    json_str = ReportGenerator.generate_json(report)
    return Response(
        content=json_str,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=originality_report_{report_id[:8]}.json"}
    )


@router.get("/report/{report_id}/csv")
async def export_csv(report_id: str):
    """
    Downloads originality report as CSV.
    """
    report = originality_comparator.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report ID not found")

    csv_str = ReportGenerator.generate_csv(report)
    return Response(
        content=csv_str,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=originality_report_{report_id[:8]}.csv"}
    )


@router.get("/report/{report_id}/pdf")
async def export_pdf(report_id: str):
    """
    Downloads originality verification report as professional PDF document.
    """
    report = originality_comparator.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report ID not found")

    pdf_bytes = ReportGenerator.generate_pdf(report)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=originality_report_{report_id[:8]}.pdf"}
    )
