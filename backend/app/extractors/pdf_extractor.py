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
from app.layout.tag_classifier import TagClassifier
from app.utils.normalization import is_ui_artifact, clean_ocr_text
from app.ocr.fraction_assembler import assemble_vertical_fractions

logger = logging.getLogger("pdf_extractor")

def is_pdf_tagged(doc: fitz.Document) -> bool:
    try:
        cat = doc.pdf_catalog()
        if cat:
            st_type, st_ref = doc.xref_get_key(cat, "StructTreeRoot")
            if st_type != "null" and st_ref:
                return True
            mi_type, mi_val = doc.xref_get_key(cat, "MarkInfo")
            if mi_type != "null" and "marked true" in mi_val.lower():
                return True
    except Exception:
        pass
    return False

MATH_PATTERNS = re.compile(r'[\u2200-\u22FF\u2A00-\u2AFF\u27C0-\u27EF×÷√∑∫∏≠≤≥±≈∞]')

def is_math_or_formula(text: Optional[str]) -> bool:
    if not text:
        return False
    t = text.strip()
    # Check for LaTeX tokens
    if any(token in t.lower() for token in ['\\frac', '\\sqrt', '\\sum', '\\int', 'mathtype']):
        return True
    # Check for genuine math operators
    if MATH_PATTERNS.search(t):
        return True
    # Mathematical equation with equals sign (excluding html/xml/comparison artifacts)
    if '=' in t and not any(tag in t for tag in ['<', '>', '==', '!=', 'http']):
        if re.search(r'\b[a-zA-Z]\s*=\s*[0-9a-zA-Z\+\-\*\/]', t):
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
        doc_is_tagged = is_pdf_tagged(doc)
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
                    f"Processing Page {page_num} of {total_pages} (Extracting text, layout & structure)..."
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

            # Step 2 — Extract Native PDF Text with Font & Layout Information
            page_dict = page.get_text("dict")
            blocks = page_dict.get("blocks", [])

            # Compute median font size for this page to accurately detect headings vs body
            page_font_sizes: List[float] = []
            for b in blocks:
                if b.get("type") == 0:
                    for line in b.get("lines", []):
                        for span in line.get("spans", []):
                            t = span.get("text", "").strip()
                            if t and len(t) >= 2:
                                page_font_sizes.append(float(span.get("size", 11.0)))

            median_body_size = TagClassifier.compute_median_font_size(page_font_sizes, fallback=11.0)
            total_native_chars = 0

            for b in blocks:
                if b.get("type") != 0:
                    continue

                # Filter out background diagonal and fragment watermark artifacts
                is_wm = False
                for line in b.get("lines", []):
                    direction = line.get("dir", (1.0, 0.0))
                    if abs(direction[1]) > 0.2:
                        l_text = "".join(s.get("text", "") for s in line.get("spans", [])).lower()
                        if any(frag in l_text for frag in ["exclusive use", "excl", "e use of", "instruc", "rs and", "ents in", "the idea", "demic p", "ership", "do not print", "do n print", "partnership"]) or len(l_text.strip()) < 15:
                            is_wm = True
                            break
                if is_wm:
                    continue

                b_raw = " ".join("".join(s.get("text", "") for s in l.get("spans", [])) for l in b.get("lines", [])).lower()
                if any(frag in b_raw for frag in ["exclusive use", "excl e use", "do not print", "do n print", "academic partnership", "evaluation only. created with aspose"]):
                    continue
                if any(frag in b_raw for frag in ["instruc", "rs and", "ents in", "demic p", "ership"]) and any(s.get("size", 0) > 20 for l in b.get("lines", []) for s in l.get("spans", [])):
                    continue

                lines = b.get("lines", [])
                block_lines_text = []
                span_fonts = []
                span_sizes = []
                span_colors = []
                span_bolds = []
                span_italics = []

                structured_lines = []
                for line in lines:
                    line_spans = line.get("spans", [])
                    span_parts = []
                    for s in line_spans:
                        st = s.get("text", "")
                        if st:
                            if span_parts and not span_parts[-1].endswith(" ") and not st.startswith(" ") and not (st and st[0] in ".,;:!?)]}%"):
                                span_parts.append(" ")
                            span_parts.append(st)
                    line_str = "".join(span_parts).strip()
                    if line_str:
                        l_bbox = line.get("bbox", (0, 0, 0, 0))
                        structured_lines.append((float(l_bbox[1]), float(l_bbox[0]), float(l_bbox[2]), line_str))
                    for s in line_spans:
                        s_text = s.get("text", "").strip()
                        if s_text:
                            s_font = s.get("font", "")
                            s_size = float(s.get("size", 11.0))
                            s_flags = int(s.get("flags", 0))
                            s_color = int(s.get("color", 0))

                            span_fonts.append(s_font)
                            span_sizes.append(s_size)
                            span_colors.append(s_color)
                            is_b = bool((s_flags & 16) or ('bold' in s_font.lower()) or ('black' in s_font.lower()) or ('heavy' in s_font.lower()))
                            is_i = bool((s_flags & 2) or ('italic' in s_font.lower()) or ('oblique' in s_font.lower()))
                            span_bolds.append(is_b)
                            span_italics.append(is_i)

                # Group lines by baseline (y0 within 4pt) and sort each baseline left-to-right by x0
                baseline_groups = []
                for y0, x0, x1, l_txt in structured_lines:
                    matched = False
                    for bg in baseline_groups:
                        if abs(y0 - bg[0][0]) <= 4.0:
                            bg.append((y0, x0, x1, l_txt))
                            matched = True
                            break
                    if not matched:
                        baseline_groups.append([(y0, x0, x1, l_txt)])

                # Assemble block lines, keeping separate lines when gap > 12 pt
                merged_block_lines = []
                for bg in baseline_groups:
                    bg.sort(key=lambda item: item[1]) # Sort left-to-right by x0
                    cur_y0, cur_x0, cur_x1, cur_txt = bg[0]
                    for item in bg[1:]:
                        iy0, ix0, ix1, itxt = item
                        if (ix0 - cur_x1) > 12 and not any(w in itxt for w in ('Then', 'where', '=')):
                            merged_block_lines.append((cur_y0, cur_x0, cur_x1, cur_txt))
                            cur_y0, cur_x0, cur_x1, cur_txt = iy0, ix0, ix1, itxt
                        else:
                            cur_x1 = max(cur_x1, ix1)
                            cur_txt = f"{cur_txt} {itxt}"
                    merged_block_lines.append((cur_y0, cur_x0, cur_x1, cur_txt))

                text_clean = "\n".join(item[3] for item in merged_block_lines).strip()
                if not text_clean:
                    continue

                # Filter out background diagonal watermark artifacts
                norm_b = text_clean.lower().replace('\n', ' ')
                if ("exclusive use" in norm_b or "excl e use" in norm_b or "do not print" in norm_b or "do n print" in norm_b) and ("partnership" in norm_b or "ership" in norm_b or "idea" in norm_b):
                    continue

                total_native_chars += len(text_clean)
                bbox = [float(b["bbox"][0]), float(b["bbox"][1]), float(b["bbox"][2]), float(b["bbox"][3])]

                dominant_font = max(set(span_fonts), key=span_fonts.count) if span_fonts else "Arial"
                dominant_size = round(sum(span_sizes) / max(1, len(span_sizes)), 1) if span_sizes else median_body_size
                dominant_bold = (span_bolds.count(True) > len(span_bolds) / 2) if span_bolds else False
                dominant_italic = (span_italics.count(True) > len(span_italics) / 2) if span_italics else False
                dominant_color_int = max(set(span_colors), key=span_colors.count) if span_colors else 0
                dominant_color_hex = f"#{dominant_color_int:06x}"

                font_info = FontInfo(
                    name=dominant_font,
                    size=dominant_size,
                    color=dominant_color_hex,
                    bold=dominant_bold,
                    italic=dominant_italic,
                    underline=False
                )

                classification = TagClassifier.classify_element(
                    text=text_clean,
                    bbox=bbox,
                    font_info=font_info,
                    page_width=page_width,
                    page_height=page_height,
                    median_body_size=median_body_size,
                    doc_is_tagged=doc_is_tagged,
                    source="native"
                )

                c_type = classification["content_type"]
                elements.append(ExtractedElement(
                    id=f"native_p{page_num}_{elem_counter}",
                    page=page_num,
                    type=c_type,
                    content_type=c_type,
                    tag=classification["tag"],
                    is_tagged=classification["is_tagged"],
                    tag_source=classification["tag_source"],
                    parameters=classification["parameters"],
                    source="native",
                    text=text_clean,
                    bbox=bbox,
                    font=font_info,
                    block_num=b.get("number", elem_counter),
                    confidence=1.0
                ))
                elem_counter += 1

                if c_type == "formula":
                    stats.formulas_count += 1
                elif c_type == "header":
                    stats.headers_count += 1
                elif c_type == "footer":
                    stats.footers_count += 1
                elif c_type == "footnote":
                    stats.footnotes_count += 1
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

                    tbl_classification = TagClassifier.classify_element(
                        is_table=True,
                        table_rows=rows,
                        table_headers=headers,
                        bbox=tab_bbox,
                        doc_is_tagged=doc_is_tagged,
                        source="native"
                    )

                    elements.append(ExtractedElement(
                        id=f"table_p{page_num}_{t_idx+1}",
                        page=page_num,
                        type="table",
                        content_type="table",
                        tag="Table",
                        is_tagged=tbl_classification["is_tagged"],
                        tag_source=tbl_classification["tag_source"],
                        parameters=tbl_classification["parameters"],
                        source="native",
                        bbox=tab_bbox,
                        headers=headers,
                        rows=rows,
                        confidence=1.0
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

                    img_classification = TagClassifier.classify_element(
                        is_image=True,
                        bbox=img_bbox,
                        doc_is_tagged=doc_is_tagged,
                        source="native",
                        image_meta={
                            "image_id": img_id,
                            "image_path": img_url,
                            "width": int(rect_info.width),
                            "height": int(rect_info.height),
                            "format": image_ext if 'image_ext' in locals() else "png"
                        }
                    )

                    elements.append(ExtractedElement(
                        id=f"image_elem_p{page_num}_{elem_counter}",
                        page=page_num,
                        type="image",
                        content_type="image",
                        tag="Figure",
                        is_tagged=True,
                        tag_source="native",
                        parameters=img_classification["parameters"],
                        source="native",
                        bbox=img_bbox,
                        image_id=img_id,
                        image_path=img_url,
                        width=int(rect_info.width),
                        height=int(rect_info.height),
                        confidence=1.0
                    ))
                    elem_counter += 1
                    stats.images_count += 1

                    if img_save_path and os.path.exists(img_save_path):
                        w_img = img_w or rect_info.width
                        h_img = img_h or rect_info.height
                        if w_img >= 28 and h_img >= 20:
                            saved_images.append({
                                "path": img_save_path,
                                "bbox": img_bbox,
                                "width": w_img,
                                "height": h_img
                            })

            # Step 4 — Smart OCR Strategy (Fast & Accurate)
            # Case A: Scanned Page (little to no native text) -> Run full-page PaddleOCR
            raw_native_text = page.get_text().strip()
            is_scanned_page = (len(raw_native_text) < 15 and total_native_chars == 0)
            if is_scanned_page:
                ocr_results = self.ocr_engine.run_ocr(page_img_path, page_num=page_num)
                for ocr_res in ocr_results:
                    raw_bbox = ocr_res.get("bbox", [0, 0, 0, 0])
                    scale = 72.0 / self.render_dpi
                    scaled_bbox = [raw_bbox[0] * scale, raw_bbox[1] * scale, raw_bbox[2] * scale, raw_bbox[3] * scale]
                    
                    ocr_text = ocr_res.get("text", "")
                    ocr_conf = ocr_res.get("confidence")
                    if is_ui_artifact(ocr_text, scaled_bbox, confidence=ocr_conf):
                        continue
                    ocr_text = clean_ocr_text(ocr_text)
                    if not ocr_text or is_ui_artifact(ocr_text, scaled_bbox, confidence=ocr_conf):
                        continue

                    ocr_classification = TagClassifier.classify_element(
                        text=ocr_text,
                        bbox=scaled_bbox,
                        page_width=page_width,
                        page_height=page_height,
                        doc_is_tagged=doc_is_tagged,
                        source="ocr"
                    )

                    elements.append(ExtractedElement(
                        id=f"ocr_p{page_num}_{elem_counter}",
                        page=page_num,
                        type=ocr_classification["content_type"],
                        content_type=ocr_classification["content_type"],
                        tag=ocr_classification["tag"],
                        is_tagged=False,
                        tag_source="ocr",
                        parameters=ocr_classification["parameters"],
                        source="ocr",
                        text=ocr_text,
                        confidence=ocr_res.get("confidence"),
                        bbox=scaled_bbox
                    ))
                    elem_counter += 1
                    if ocr_classification["content_type"] == "formula":
                        stats.formulas_count += 1
                    stats.ocr_text_blocks += 1
            else:
                # Case B: Digital Native Page -> Run OCR specifically on extracted images/formulas (10x faster)
                for s_img in saved_images:
                    try:
                        img_path_for_ocr = s_img["path"]
                        scale_m = 1.0
                        try:
                            with Image.open(s_img["path"]) as test_im:
                                w_im, h_im = test_im.size
                                if w_im < 28 or h_im < 20:
                                    continue
                                if h_im < 160 or w_im < 160:
                                    scale_factor = max(2, min(5, int(220 / max(1, h_im))))
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
                        crop_results = assemble_vertical_fractions(crop_results)
                        img_bbox = s_img["bbox"]
                        iw = max(1.0, img_bbox[2] - img_bbox[0])
                        ih = max(1.0, img_bbox[3] - img_bbox[1])
                        crop_w = max(1.0, float(s_img["width"]))
                        crop_h = max(1.0, float(s_img["height"]))

                        pad_b = 15.0 if scale_m > 1.0 else 0.0
                        scaled_w = max(1.0, crop_w * scale_m)
                        scaled_h = max(1.0, crop_h * scale_m)

                        for crop_res in crop_results:
                            crop_text = crop_res.get("text", "").strip()
                            if not crop_text:
                                continue
                            c_bbox = crop_res.get("bbox", [0, 0, 0, 0])
                            crop_conf = crop_res.get("confidence")

                            norm_x0 = max(0.0, (c_bbox[0] - pad_b) / scaled_w)
                            norm_y0 = max(0.0, (c_bbox[1] - pad_b) / scaled_h)
                            norm_x1 = min(1.0, (c_bbox[2] - pad_b) / scaled_w)
                            norm_y1 = min(1.0, (c_bbox[3] - pad_b) / scaled_h)

                            mapped_bbox = [
                                img_bbox[0] + norm_x0 * iw,
                                img_bbox[1] + norm_y0 * ih,
                                img_bbox[0] + norm_x1 * iw,
                                img_bbox[1] + norm_y1 * ih
                            ]

                            if is_ui_artifact(crop_text, mapped_bbox, confidence=crop_conf):
                                continue
                            crop_text = clean_ocr_text(crop_text)
                            if not crop_text or is_ui_artifact(crop_text, mapped_bbox, confidence=crop_conf):
                                continue

                            is_frac_formula = bool(crop_res.get("is_formula", False))
                            crop_classification = TagClassifier.classify_element(
                                text=crop_text,
                                bbox=mapped_bbox,
                                page_width=page_width,
                                page_height=page_height,
                                is_formula=is_frac_formula,
                                doc_is_tagged=doc_is_tagged,
                                source="ocr"
                            )

                            elements.append(ExtractedElement(
                                id=f"ocr_img_p{page_num}_{elem_counter}",
                                page=page_num,
                                type=crop_classification["content_type"],
                                content_type=crop_classification["content_type"],
                                tag=crop_classification["tag"],
                                is_tagged=False,
                                tag_source="ocr",
                                parameters=crop_classification["parameters"],
                                source="ocr",
                                text=crop_text,
                                confidence=crop_res.get("confidence"),
                                bbox=mapped_bbox
                            ))
                            elem_counter += 1
                            if crop_classification["content_type"] == "formula":
                                stats.formulas_count += 1
                            stats.ocr_text_blocks += 1
                    except Exception as ex_crop:
                        logger.debug(f"Image crop OCR note: {ex_crop}")

            # Step 5 — PP-Structure Layout Engine (for scanned pages or unformatted documents)
            if is_scanned_page:
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
                            stats.tables_count += 1
                        elif st_type == "figure":
                            continue
                        else:
                            stats.pp_structure_regions += 1

                        pp_classification = TagClassifier.classify_element(
                            text=struct_res.get("text"),
                            bbox=scaled_bbox,
                            is_table=(st_type == "table"),
                            is_formula=(st_type == "formula"),
                            page_width=page_width,
                            page_height=page_height,
                            doc_is_tagged=doc_is_tagged,
                            source="pp_structure"
                        )

                        elements.append(ExtractedElement(
                            id=f"pp_p{page_num}_{elem_counter}",
                            page=page_num,
                            type=pp_classification["content_type"],
                            content_type=pp_classification["content_type"],
                            tag=pp_classification["tag"],
                            is_tagged=False,
                            tag_source="pp_structure",
                            parameters=pp_classification["parameters"],
                            source="pp_structure",
                            text=struct_res.get("text"),
                            bbox=scaled_bbox
                        ))
                        elem_counter += 1
                except Exception as ex_struct:
                    logger.debug(f"PPStructure layout note: {ex_struct}")
            elif stats.tables_count == 0:
                try:
                    structure_results = self.structure_engine.analyze_structure(page_img_path, page_num=page_num)
                    for struct_res in structure_results:
                        st_type = struct_res.get("type", "").lower()
                        if st_type == "table":
                            raw_bbox = struct_res.get("bbox", [0, 0, 0, 0])
                            scale = 72.0 / self.render_dpi
                            scaled_bbox = [raw_bbox[0] * scale, raw_bbox[1] * scale, raw_bbox[2] * scale, raw_bbox[3] * scale]

                            pp_tbl_classification = TagClassifier.classify_element(
                                text=struct_res.get("text"),
                                bbox=scaled_bbox,
                                is_table=True,
                                page_width=page_width,
                                page_height=page_height,
                                doc_is_tagged=doc_is_tagged,
                                source="pp_structure"
                            )

                            elements.append(ExtractedElement(
                                id=f"pp_tab_p{page_num}_{elem_counter}",
                                page=page_num,
                                type="table",
                                content_type="table",
                                tag="Table",
                                is_tagged=False,
                                tag_source="pp_structure",
                                parameters=pp_tbl_classification["parameters"],
                                source="pp_structure",
                                text=struct_res.get("text"),
                                bbox=scaled_bbox
                            ))
                            elem_counter += 1
                            stats.tables_count += 1
                except Exception as ex_struct:
                    logger.debug(f"PPStructure table check note: {ex_struct}")

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

        all_extracted_elements = [elem for p in pages_data for elem in p.elements]
        tagging_summary = TagClassifier.build_tagging_summary(all_extracted_elements, doc_is_tagged=doc_is_tagged)

        return {
            "pages": pages_data,
            "statistics": stats,
            "is_tagged_document": doc_is_tagged,
            "tagging_summary": tagging_summary
        }
