import os
import re
import logging
from typing import List, Dict, Any, Optional, Callable
import pymupdf as fitz
from PIL import Image

from app.models.extraction_models import PageData, ExtractedElement, FontInfo, ExtractionStatistics
from app.ocr.paddle_ocr_engine import PaddleOCREngine
from app.ocr.pp_structure_engine import PPStructureEngine
from app.layout.overlap_detector import detect_overlaps
from app.layout.duplicate_detector import detect_duplicates
from app.layout.reading_order import sort_reading_order
from app.utils.normalization import is_ui_artifact, clean_ocr_text

logger = logging.getLogger("pdf_extractor")

MATH_PATTERNS = re.compile(r'[\u2200-\u22FF\u2A00-\u2AFF\u27C0-\u27EF\u0370-\u03FF=+\-×÷√∑∫∏≠≤≥±≈∞]')

def is_math_or_formula(text: Optional[str]) -> bool:
    if not text:
        return False
    # Check for math symbols, equation signs, LaTeX tokens
    if MATH_PATTERNS.search(text) and ('=' in text or len(text.strip()) > 3):
        return True
    if any(token in text.lower() for token in ['\\frac', '\\sqrt', '\\sum', '\\int', 'mathtype', 'equation']):
        return True
    return False

class PDFExtractor:
    def __init__(
        self,
        ocr_engine: Optional[PaddleOCREngine] = None,
        structure_engine: Optional[PPStructureEngine] = None,
        render_dpi: int = 200
    ):
        self.ocr_engine = ocr_engine or PaddleOCREngine()
        self.structure_engine = structure_engine or PPStructureEngine()
        self.render_dpi = render_dpi

    def extract_pdf(
        self,
        pdf_path: str,
        temp_dir: str,
        progress_callback: Optional[Callable[[str, int, Optional[int], Optional[int], Optional[str]], None]] = None
    ) -> Dict[str, Any]:
        job_id = os.path.basename(temp_dir)
        doc = fitz.open(pdf_path)
        pages_data: List[PageData] = []
        stats = ExtractionStatistics()
        total_pages = len(doc)
        stats.total_pages = total_pages

        for page_idx in range(total_pages):
            page_num = page_idx + 1
            page = doc[page_idx]
            rect = page.rect
            page_width, page_height = float(rect.width), float(rect.height)
            
            # Granular real-time progress update for each page
            if progress_callback:
                page_pct = 15 + int((page_idx / max(1, total_pages)) * 75)
                progress_callback(
                    "page_processing",
                    page_pct,
                    page_num,
                    total_pages,
                    f"Processing Page {page_num} of {total_pages} (Extracting text, formulas & images)..."
                )

            elements: List[ExtractedElement] = []
            elem_counter = 1

            # Step 1 — Render high-DPI original page image for preview and visual fidelity
            zoom = self.render_dpi / 72.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            page_img_filename = f"page_{page_num}.png"
            page_img_path = os.path.join(temp_dir, page_img_filename)
            pix.save(page_img_path)

            # Step 2 — Extract Native PDF Text
            text_page = page.get_text("blocks")
            total_native_chars = 0
            for block in text_page:
                x0, y0, x1, y1, text, block_no, block_type = block[:7]
                text_clean = text.strip()
                if not text_clean:
                    continue

                # Filter out background diagonal watermark artifacts
                norm_b = text_clean.lower().replace('\n', ' ')
                if ("exclusive use" in norm_b or "excl e use" in norm_b or "do not print" in norm_b or "do n print" in norm_b) and ("partnership" in norm_b or "ership" in norm_b or "idea" in norm_b):
                    continue
                    
                total_native_chars += len(text_clean)
                bbox = [float(x0), float(y0), float(x1), float(y1)]
                font_info = None
                
                is_formula = is_math_or_formula(text_clean)
                elem_type = "formula" if is_formula else "text"
                
                elements.append(ExtractedElement(
                    id=f"native_p{page_num}_{elem_counter}",
                    page=page_num,
                    type=elem_type,
                    source="native",
                    text=text_clean,
                    bbox=bbox,
                    font=font_info,
                    block_num=block_no
                ))
                elem_counter += 1
                if is_formula:
                    stats.formulas_count += 1
                else:
                    stats.native_text_blocks += 1

            # Step 2b — Instantaneous Native Table Extraction using PyMuPDF built-in TableFinder
            try:
                tables = page.find_tables()
                for t_idx, tab in enumerate(tables):
                    tab_bbox = [float(tab.bbox[0]), float(tab.bbox[1]), float(tab.bbox[2]), float(tab.bbox[3])]
                    tab_data = tab.extract()
                    headers = [str(c or '') for c in tab_data[0]] if tab_data else []
                    rows = [[str(c or '') for c in r] for r in tab_data[1:]] if len(tab_data) > 1 else []
                    elements.append(ExtractedElement(
                        id=f"table_p{page_num}_{t_idx+1}",
                        page=page_num,
                        type="table",
                        source="native",
                        bbox=tab_bbox,
                        headers=headers,
                        rows=rows
                    ))
                    elem_counter += 1
                    stats.tables_count += 1
            except Exception as ex_tab:
                logger.debug(f"Native table extraction note: {ex_tab}")

            # Step 3 — Extract All PDF Images (Normal & MathType images)
            image_list = page.get_images(full=True)
            saved_images: List[Dict[str, Any]] = []

            for img_idx, img_info in enumerate(image_list):
                xref = img_info[0]
                img_rects = page.get_image_rects(xref)
                
                img_url = None
                img_save_path = None
                img_w = 0
                img_h = 0
                try:
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image.get("image")
                    image_ext = base_image.get("ext", "png")
                    img_w = base_image.get("width", 0)
                    img_h = base_image.get("height", 0)
                    img_filename = f"pdf_img_p{page_num}_{img_idx+1}.{image_ext}"
                    img_save_path = os.path.join(temp_dir, img_filename)
                    if image_bytes:
                        with open(img_save_path, "wb") as f:
                            f.write(image_bytes)
                        img_url = f"/api/image/{job_id}/{img_filename}"
                except Exception as ex:
                    logger.warning(f"Could not extract image bytes for xref {xref}: {ex}")

                for rect_info in img_rects:
                    img_bbox = [float(rect_info.x0), float(rect_info.y0), float(rect_info.x1), float(rect_info.y1)]
                    img_id = f"img_p{page_num}_{img_idx+1}"
                    
                    elements.append(ExtractedElement(
                        id=f"image_elem_p{page_num}_{elem_counter}",
                        page=page_num,
                        type="image",
                        source="native",
                        bbox=img_bbox,
                        image_id=img_id,
                        image_path=img_url,
                        width=int(rect_info.width),
                        height=int(rect_info.height)
                    ))
                    elem_counter += 1
                    stats.images_count += 1

                    if img_save_path and os.path.exists(img_save_path):
                        saved_images.append({
                            "path": img_save_path,
                            "bbox": img_bbox,
                            "width": img_w or rect_info.width,
                            "height": img_h or rect_info.height
                        })

            # Step 4 — Smart OCR Strategy (Fast & Accurate)
            # Case A: Scanned Page (little to no native text) -> Run full-page PaddleOCR
            is_scanned_page = total_native_chars < 50
            if is_scanned_page:
                ocr_results = self.ocr_engine.run_ocr(page_img_path, page_num=page_num)
                for ocr_res in ocr_results:
                    raw_bbox = ocr_res.get("bbox", [0, 0, 0, 0])
                    scale = 72.0 / self.render_dpi
                    scaled_bbox = [raw_bbox[0] * scale, raw_bbox[1] * scale, raw_bbox[2] * scale, raw_bbox[3] * scale]
                    
                    ocr_text = ocr_res.get("text", "")
                    if is_ui_artifact(ocr_text, scaled_bbox):
                        continue
                    ocr_text = clean_ocr_text(ocr_text)
                    if not ocr_text:
                        continue
                    is_formula = is_math_or_formula(ocr_text)
                    elem_type = "formula" if is_formula else "image_text"

                    elements.append(ExtractedElement(
                        id=f"ocr_p{page_num}_{elem_counter}",
                        page=page_num,
                        type=elem_type,
                        source="ocr",
                        text=ocr_text,
                        confidence=ocr_res.get("confidence"),
                        bbox=scaled_bbox
                    ))
                    elem_counter += 1
                    if is_formula:
                        stats.formulas_count += 1
                    stats.ocr_text_blocks += 1
            else:
                # Case B: Digital Native Page -> Run OCR specifically on extracted images/formulas (10x faster)
                for s_img in saved_images:
                    try:
                        img_path_for_ocr = s_img["path"]
                        scale_m = 1.0
                        # Auto-upscale small equation/image crops so OCR text detector does not miss them
                        try:
                            with Image.open(s_img["path"]) as test_im:
                                w_im, h_im = test_im.size
                                if h_im < 120 or w_im < 120:
                                    scale_factor = max(2, min(5, int(180 / max(1, h_im))))
                                    scale_m = float(scale_factor)
                                    upscaled_im = test_im.resize((w_im * scale_factor, h_im * scale_factor), Image.Resampling.LANCZOS)
                                    from PIL import ImageOps
                                    padded_im = ImageOps.expand(upscaled_im, border=15, fill='white')
                                    upscaled_path = s_img["path"] + "_upscaled.png"
                                    padded_im.save(upscaled_path)
                                    img_path_for_ocr = upscaled_path
                        except Exception:
                            img_path_for_ocr = s_img["path"]

                        crop_results = self.ocr_engine.run_ocr(img_path_for_ocr, page_num=page_num)
                        img_bbox = s_img["bbox"]
                        iw = max(1.0, img_bbox[2] - img_bbox[0])
                        ih = max(1.0, img_bbox[3] - img_bbox[1])
                        crop_w = max(1.0, float(s_img["width"]))
                        crop_h = max(1.0, float(s_img["height"]))

                        for crop_res in crop_results:
                            crop_text = crop_res.get("text", "").strip()
                            if not crop_text:
                                continue
                            c_bbox = crop_res.get("bbox", [0, 0, 0, 0])
                            if is_ui_artifact(crop_text, c_bbox):
                                continue
                            crop_text = clean_ocr_text(crop_text)
                            if not crop_text:
                                continue
                            # Map crop coordinates back to page coordinate space
                            mapped_bbox = [
                                img_bbox[0] + (c_bbox[0] / crop_w) * iw,
                                img_bbox[1] + (c_bbox[1] / crop_h) * ih,
                                img_bbox[0] + (c_bbox[2] / crop_w) * iw,
                                img_bbox[1] + (c_bbox[3] / crop_h) * ih
                            ]
                            is_formula = is_math_or_formula(crop_text)
                            elem_type = "formula" if is_formula else "image_text"

                            elements.append(ExtractedElement(
                                id=f"ocr_img_p{page_num}_{elem_counter}",
                                page=page_num,
                                type=elem_type,
                                source="ocr",
                                text=crop_text,
                                confidence=crop_res.get("confidence"),
                                bbox=mapped_bbox
                            ))
                            elem_counter += 1
                            if is_formula:
                                stats.formulas_count += 1
                            stats.ocr_text_blocks += 1
                    except Exception as ex_crop:
                        logger.debug(f"Image crop OCR note: {ex_crop}")

            # Step 5 — PP-Structure Layout Engine (for scanned pages or unformatted documents)
            if is_scanned_page or stats.tables_count == 0:
                try:
                    structure_results = self.structure_engine.analyze_structure(page_img_path, page_num=page_num)
                    for struct_res in structure_results:
                        raw_bbox = struct_res.get("bbox", [0, 0, 0, 0])
                        scale = 72.0 / self.render_dpi
                        scaled_bbox = [raw_bbox[0] * scale, raw_bbox[1] * scale, raw_bbox[2] * scale, raw_bbox[3] * scale]
                        
                        st_type = struct_res.get("type", "text")
                        if st_type in ("equation", "formula"):
                            st_type = "formula"
                            stats.formulas_count += 1
                        elif st_type == "table":
                            # Only add if not already captured natively
                            if is_scanned_page:
                                stats.tables_count += 1
                            else:
                                continue
                        else:
                            stats.pp_structure_regions += 1

                        elements.append(ExtractedElement(
                            id=f"pp_p{page_num}_{elem_counter}",
                            page=page_num,
                            type=st_type,
                            source="pp_structure",
                            text=struct_res.get("text"),
                            bbox=scaled_bbox
                        ))
                        elem_counter += 1
                except Exception as ex_struct:
                    logger.debug(f"PPStructure layout note: {ex_struct}")

            # Step 6 — Overlap Detection & Classification
            elements = detect_overlaps(elements)

            # Step 7 — Duplicate Detection
            elements = detect_duplicates(elements)
            stats.possible_duplicates_count += sum(1 for e in elements if e.possible_duplicate)

            # Step 8 — Reading Order Engine
            elements = sort_reading_order(elements, page_width=page_width)

            pages_data.append(PageData(
                page=page_num,
                width=page_width,
                height=page_height,
                elements=elements,
                rendered_image_url=f"/api/preview/{job_id}/{page_num}"
            ))

        doc.close()

        return {
            "pages": pages_data,
            "statistics": stats
        }
