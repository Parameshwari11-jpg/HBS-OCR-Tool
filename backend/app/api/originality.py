import logging
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

logger = logging.getLogger("originality_api")
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

        # Ensure original file is permanently accessible in report temp directory for injection/export
        try:
            report_dir = get_job_temp_dir(report.report_id)
            ext = os.path.splitext(orig_path)[1].lower()
            persistent_orig = report_dir / f"original{ext}"
            if str(persistent_orig) != orig_path and not persistent_orig.exists():
                shutil.copyfile(orig_path, str(persistent_orig))
                report.original_doc_path = str(persistent_orig)
        except Exception as e_copy:
            logger.warning(f"Could not persist original file for report {report.report_id}: {e_copy}")

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


@router.post("/inject-invisible-text/{report_id}")
async def inject_invisible_text(report_id: str):
    """
    Injects extracted text as an invisible search/copy text layer behind all images in the PDF.
    Preserves 100% original visual layout without overlapping or altering existing visible content.
    """
    report = originality_comparator.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Originality report not found")

    # 1. Resolve source PDF
    pdf_source: Optional[str] = None
    if report.original_doc_path and os.path.exists(report.original_doc_path) and report.original_doc_path.lower().endswith(".pdf"):
        pdf_source = report.original_doc_path
    elif report.job_id:
        cand = get_job_temp_dir(report.job_id) / "original_converted.pdf"
        if cand.exists():
            pdf_source = str(cand)

    if not pdf_source:
        report_dir = get_job_temp_dir(report_id)
        cand_rep = report_dir / "original.pdf"
        if cand_rep.exists():
            pdf_source = str(cand_rep)

    if not pdf_source or not os.path.exists(pdf_source):
        raise HTTPException(status_code=404, detail="Original PDF source not found for invisible text injection")

    # 2. Map extracted text and positions per page
    # Try loading extraction job result if available for rich coordinates
    job_result = None
    if report.job_id:
        try:
            job_result = job_service.get_result(report.job_id)
        except Exception as e_job:
            logger.debug(f"Could not load job result for coordinates: {e_job}")

    report_dir = get_job_temp_dir(report_id)
    output_pdf_path = str(report_dir / f"injected_{report.original_filename}")

    try:
        doc = pymupdf.open(pdf_source)

        for page_result in report.pages:
            p_idx = page_result.page - 1
            if p_idx < 0 or p_idx >= len(doc):
                continue
            page = doc[p_idx]
            init_xrefs = page.get_contents()

            # Collect items to inject on this page: list of (Point(x, y), text, fontsize, morph)
            items_to_inject = []

            # Check if this page already has native text to prevent duplicate stacking
            existing_native_text = page.get_text().strip()
            helv_font = pymupdf.Font("helv")

            from app.utils.spacing_engine import SpacingEngine
            from app.layout.reading_order import sort_reading_order
            spacing_engine = SpacingEngine.get_instance()

            if job_result and p_idx < len(job_result.pages):
                p_data = job_result.pages[p_idx]
                valid_elems = []
                for elem in p_data.elements:
                    txt = (elem.text or "").strip()
                    if not txt:
                        continue
                    if existing_native_text and txt in existing_native_text:
                        continue
                    valid_elems.append(elem)

                sorted_elems = sort_reading_order(valid_elems, page_width=page.rect.width)
                num_elems = len(sorted_elems)
                for i, elem in enumerate(sorted_elems):
                    txt = (elem.text or "").strip()
                    bbox = elem.bbox or [50.0, 50.0, 300.0, 70.0]
                    x0, y0, x1, y1 = bbox
                    box_w = max(1.0, float(x1 - x0))
                    box_h = max(8.0, float(y1 - y0))
                    fs = box_h * 0.92
                    y_baseline = y1 - (box_h * 0.08)
                    pt = pymupdf.Point(x0, y_baseline)

                    if i < num_elems - 1:
                        next_elem = sorted_elems[i + 1]
                        next_txt = (next_elem.text or "").strip()
                        next_bbox = next_elem.bbox or [50.0, 50.0, 300.0, 70.0]
                        e1_yc = (y0 + y1) / 2.0
                        e2_yc = (next_bbox[1] + next_bbox[3]) / 2.0
                        same_line = abs(e1_yc - e2_yc) <= max(4.0, 0.45 * min(box_h, float(next_bbox[3] - next_bbox[1])))
                        if same_line and next_bbox[0] >= x1:
                            coord_gap = float(next_bbox[0] - x1)
                        else:
                            coord_gap = None
                        if spacing_engine.should_insert_space(txt, next_txt, coord_gap=coord_gap, font_size=fs):
                            txt = txt + " "
                    else:
                        last_c = txt[-1] if txt else ""
                        if last_c and last_c not in "-–—'’([{‘“«$#@":
                            txt = txt + " "

                    tw = helv_font.text_length(txt, fontsize=fs)
                    sx = box_w / max(0.1, tw)
                    morph = (pt, pymupdf.Matrix(sx, 1.0))
                    items_to_inject.append((pt, txt, fs, morph))
            elif page_result.line_positions:
                num_lps = len(page_result.line_positions)
                for i, lp in enumerate(page_result.line_positions):
                    txt = lp.get("text", "").strip()
                    if not txt:
                        continue
                    if existing_native_text and txt in existing_native_text:
                        continue
                    x0 = float(lp.get("x0", 50.0))
                    y0 = float(lp.get("y0", 50.0))
                    x1 = float(lp.get("x1", x0 + 100.0))
                    y1 = float(lp.get("y1", y0 + 15.0))
                    box_w = max(1.0, float(x1 - x0))
                    box_h = max(8.0, float(y1 - y0))
                    fs = box_h * 0.92
                    y_baseline = y1 - (box_h * 0.08)
                    pt = pymupdf.Point(x0, y_baseline)

                    if i < num_lps - 1:
                        next_txt = page_result.line_positions[i + 1].get("text", "").strip()
                        if spacing_engine.should_insert_space(txt, next_txt, font_size=fs):
                            txt = txt + " "
                    else:
                        last_c = txt[-1] if txt else ""
                        if last_c and last_c not in "-–—'’([{‘“«$#@":
                            txt = txt + " "

                    tw = helv_font.text_length(txt, fontsize=fs)
                    sx = box_w / max(0.1, tw)
                    morph = (pt, pymupdf.Matrix(sx, 1.0))
                    items_to_inject.append((pt, txt, fs, morph))
            else:
                # Fallback: distribute extracted lines cleanly down the page
                page_h = page.rect.height
                page_w = page.rect.width
                line_count = max(1, len(page_result.extracted_lines))
                line_spacing = min(22.0, max(12.0, (page_h - 100.0) / line_count))
                cur_y = 50.0
                num_lines = len(page_result.extracted_lines)
                for i, line_txt in enumerate(page_result.extracted_lines):
                    txt = line_txt.strip()
                    if not txt:
                        cur_y += line_spacing
                        continue
                    if existing_native_text and txt in existing_native_text:
                        cur_y += line_spacing
                        continue
                    fs = min(14.0, line_spacing * 0.8)
                    pt = pymupdf.Point(50.0, cur_y + line_spacing * 0.8)

                    if i < num_lines - 1:
                        next_txt = page_result.extracted_lines[i + 1].strip()
                        if spacing_engine.should_insert_space(txt, next_txt, font_size=fs):
                            txt = txt + " "
                    else:
                        last_c = txt[-1] if txt else ""
                        if last_c and last_c not in "-–—'’([{‘“«$#@":
                            txt = txt + " "

                    items_to_inject.append((pt, txt, fs, None))
                    cur_y += line_spacing

            if not items_to_inject:
                continue

            # Insert invisible text using PDF render_mode=3 (neither fill nor stroke)
            for pt, txt, fs, morph in items_to_inject:
                try:
                    if morph:
                        page.insert_text(pt, txt, fontsize=fs, render_mode=3, morph=morph)
                    else:
                        page.insert_text(pt, txt, fontsize=fs, render_mode=3)
                except Exception as e_ins:
                    logger.debug(f"Failed inserting single text token: {e_ins}")

            # Inject tag-ready vector paths for non-text elements (images, figures, drawings, shapes, lines, flags)
            # Each element gets its own independent vector path so Adobe Acrobat can select and tag each one individually without PitStop
            if job_result and p_idx < len(job_result.pages):
                non_text_elements = [
                    elem for elem in job_result.pages[p_idx].elements
                    if elem.type in ("image", "figure", "drawing", "shape", "line")
                    or elem.tag in ("Image", "Figure")
                ]
                pw_cur = float(page.rect.width)
                ph_cur = float(page.rect.height)
                for elem in non_text_elements:
                    if elem.bbox and len(elem.bbox) == 4:
                        bx0, by0, bx1, by1 = elem.bbox
                        bw = bx1 - bx0
                        bh = by1 - by0
                        # Skip full-page background scans or massive container images (> 65% of page width AND height, or > 80% width, or > 80% height)
                        # so they don't cover child elements like flags, photos, boxes, and icons
                        if (bw >= 0.65 * pw_cur and bh >= 0.65 * ph_cur) or (bw >= 0.80 * pw_cur and bh >= 0.40 * ph_cur) or (bh >= 0.80 * ph_cur and bw >= 0.40 * pw_cur):
                            continue
                        if bw >= 4.0 and bh >= 4.0:
                            try:
                                elem_shape = page.new_shape()
                                elem_shape.draw_rect(pymupdf.Rect(bx0, by0, bx1, by1))
                                elem_shape.finish(width=0.5, stroke_opacity=0.001)
                                elem_shape.commit()
                            except Exception:
                                pass

            # Reorder page content streams so newly injected text streams are placed FIRST (behind all images/graphics)
            post_xrefs = page.get_contents()
            new_xrefs = [x for x in post_xrefs if x not in init_xrefs]
            if new_xrefs and init_xrefs:
                reordered = new_xrefs + init_xrefs
                contents_str = "[" + " ".join(f"{x} 0 R" for x in reordered) + "]"
                doc.xref_set_key(page.xref, "Contents", contents_str)

            # Consolidate and sanitize page content stream to ensure strict ISO 32000 / PDF-UA compliance
            # (Places 'cm' transformation operators outside 'BT...ET' text objects)
            try:
                page.clean_contents()
            except Exception:
                pass

        doc.save(output_pdf_path)
        doc.close()

        base_fn = os.path.splitext(report.original_filename)[0]
        download_fn = f"{base_fn}_with_invisible_text.pdf"

        return FileResponse(
            path=output_pdf_path,
            media_type="application/pdf",
            filename=download_fn,
            headers={"Content-Disposition": f"attachment; filename=\"{download_fn}\""}
        )

    except Exception as e:
        logger.error(f"Error injecting invisible text: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to inject invisible text: {str(e)}")
