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


@router.get("/{job_id}/inject-pdf")
@router.post("/{job_id}/inject-pdf")
async def export_injected_pdf(job_id: str):
    """
    Injects extracted text directly behind image layers into the original uploaded PDF.
    Can be used right after text extraction, before or without running originality check.
    """
    import os
    from pathlib import Path
    import pymupdf
    from fastapi.responses import FileResponse
    from app.utils.file_utils import get_upload_dir, get_job_temp_dir
    from app.utils.spacing_engine import SpacingEngine
    from app.layout.reading_order import sort_reading_order

    result = job_service.get_result(job_id)
    if not result:
        raise HTTPException(status_code=404, detail="Results not found for job ID")

    # 1. Resolve source PDF
    pdf_source = None
    upload_dir = get_upload_dir()
    for ext in [".pdf", ".PDF"]:
        cand = upload_dir / f"{job_id}{ext}"
        if cand.exists():
            pdf_source = str(cand)
            break

    if not pdf_source:
        cand_conv = get_job_temp_dir(job_id) / "original_converted.pdf"
        if cand_conv.exists():
            pdf_source = str(cand_conv)

    if not pdf_source or not os.path.exists(pdf_source):
        raise HTTPException(status_code=404, detail="Original PDF file not found for injection")

    temp_dir = get_job_temp_dir(job_id)
    output_pdf_path = str(temp_dir / f"injected_{result.filename}")

    try:
        doc = pymupdf.open(pdf_source)
        helv_font = pymupdf.Font("helv")

        spacing_engine = SpacingEngine.get_instance()

        for p_idx, p_data in enumerate(result.pages):
            if p_idx >= len(doc):
                break
            page = doc[p_idx]
            init_xrefs = page.get_contents()
            existing_native_text = page.get_text().strip()

            # Filter valid text elements for this page
            valid_elems = []
            for elem in p_data.elements:
                txt = (elem.text or "").strip()
                if not txt:
                    continue
                if existing_native_text and txt in existing_native_text:
                    continue
                valid_elems.append(elem)

            if not valid_elems:
                continue

            # Ensure elements are sorted in natural reading order
            sorted_elems = sort_reading_order(valid_elems, page_width=page.rect.width)

            items_to_inject = []
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

                # Determine if a trailing space is required between this element and the next element
                if i < num_elems - 1:
                    next_elem = sorted_elems[i + 1]
                    next_txt = (next_elem.text or "").strip()
                    next_bbox = next_elem.bbox or [50.0, 50.0, 300.0, 70.0]
                    
                    # Check if elements are on the same line
                    e1_yc = (y0 + y1) / 2.0
                    e2_yc = (next_bbox[1] + next_bbox[3]) / 2.0
                    same_line = abs(e1_yc - e2_yc) <= max(4.0, 0.45 * min(box_h, float(next_bbox[3] - next_bbox[1])))
                    
                    # Horizontal gap if on the same line and next is to the right
                    if same_line and next_bbox[0] >= x1:
                        coord_gap = float(next_bbox[0] - x1)
                    else:
                        coord_gap = None
                    
                    if spacing_engine.should_insert_space(txt, next_txt, coord_gap=coord_gap, font_size=fs):
                        txt = txt + " "
                else:
                    # Trailing element on page: check if element ends at a standalone boundary
                    last_c = txt[-1] if txt else ""
                    if last_c and last_c not in "-–—'’([{‘“«$#@":
                        txt = txt + " "

                tw = helv_font.text_length(txt, fontsize=fs)
                sx = box_w / max(0.1, tw)
                morph = (pt, pymupdf.Matrix(sx, 1.0))
                items_to_inject.append((pt, txt, fs, morph))

            for pt, txt, fs, morph in items_to_inject:
                try:
                    if morph:
                        page.insert_text(pt, txt, fontsize=fs, render_mode=3, morph=morph)
                    else:
                        page.insert_text(pt, txt, fontsize=fs, render_mode=3)
                except Exception:
                    pass

            # Place newly injected invisible text streams BEHIND all images
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

        base_fn = os.path.splitext(result.filename)[0]
        download_fn = f"{base_fn}_with_invisible_text.pdf"

        return FileResponse(
            path=output_pdf_path,
            media_type="application/pdf",
            filename=download_fn,
            headers={"Content-Disposition": f'attachment; filename="{download_fn}"'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to inject invisible layer: {str(e)}")

