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

            # Pre-detect horizontal fraction lines from PDF drawings
            drawings = page.get_drawings()
            frac_bars = [
                (d["rect"].x0, (d["rect"].y0 + d["rect"].y1) / 2.0, d["rect"].x1, d["rect"].y0, d["rect"].y1)
                for d in drawings
                if abs(d["rect"].y1 - d["rect"].y0) <= 3.0 and 5.0 <= (d["rect"].x1 - d["rect"].x0) <= 65.0
            ]

            def split_block_into_column_subblocks(b: Dict[str, Any]) -> List[Dict[str, Any]]:
                lines = b.get("lines", [])
                if not lines or len(lines) <= 1:
                    return [b]
                x_ranges = [(l["bbox"][0], l["bbox"][2]) for l in lines]
                min_x0 = min(r[0] for r in x_ranges)
                max_x0 = max(r[0] for r in x_ranges)
                if max_x0 - min_x0 < 45.0:
                    return [b]
                col_clusters = []
                for l in lines:
                    placed = False
                    lx0, lx1 = l["bbox"][0], l["bbox"][2]
                    for col in col_clusters:
                        col_x0 = min(item["bbox"][0] for item in col)
                        col_x1 = max(item["bbox"][2] for item in col)
                        if not (lx1 < col_x0 - 25.0 or lx0 > col_x1 + 25.0):
                            col.append(l)
                            placed = True
                            break
                    if not placed:
                        col_clusters.append([l])
                if len(col_clusters) <= 1:
                    return [b]
                sub_blocks = []
                for col_lines in col_clusters:
                    new_b = dict(b)
                    new_b["lines"] = col_lines
                    new_b["bbox"] = (
                        min(l["bbox"][0] for l in col_lines),
                        min(l["bbox"][1] for l in col_lines),
                        max(l["bbox"][2] for l in col_lines),
                        max(l["bbox"][3] for l in col_lines),
                    )
                    sub_blocks.append(new_b)
                return sub_blocks

            raw_valid_blocks = [b for b in blocks if b.get("type") == 0]
            valid_blocks = []
            for rb in raw_valid_blocks:
                valid_blocks.extend(split_block_into_column_subblocks(rb))
            clusters = []
            assigned = set()

            for i, b in enumerate(valid_blocks):
                if i in assigned:
                    continue
                bb = b.get("bbox", (0, 0, 0, 0))
                has_bar = any(bb[0] - 5 <= fb[0] and fb[2] <= bb[2] + 5 and bb[1] - 5 <= fb[1] <= bb[3] + 5 for fb in frac_bars)
                if not has_bar:
                    clusters.append([b])
                    assigned.add(i)
                    continue

                row_group = [i]
                assigned.add(i)
                for j, ob in enumerate(valid_blocks):
                    if j in assigned:
                        continue
                    obb = ob.get("bbox", (0, 0, 0, 0))
                    v_overlap = max(0.0, min(bb[3], obb[3]) - max(bb[1], obb[1]))
                    if v_overlap > 3.0:
                        row_group.append(j)
                        assigned.add(j)
                clusters.append([valid_blocks[k] for k in row_group])

            for cl in clusters:
                # Filter out background diagonal and fragment watermark artifacts
                cl_is_wm = False
                for b in cl:
                    for line in b.get("lines", []):
                        direction = line.get("dir", (1.0, 0.0))
                        if abs(direction[1]) > 0.2:
                            l_text = "".join(s.get("text", "") for s in line.get("spans", [])).lower()
                            if any(frag in l_text for frag in ["exclusive use", "excl", "e use of", "instruc", "rs and", "ents in", "the idea", "demic p", "ership", "do not print", "do n print", "partnership"]) or len(l_text.strip()) < 15:
                                cl_is_wm = True
                                break
                    if cl_is_wm:
                        break
                if cl_is_wm:
                    continue

                b_raw = " ".join("".join(s.get("text", "") for s in l.get("spans", [])) for b in cl for l in b.get("lines", [])).lower()
                if any(frag in b_raw for frag in ["exclusive use", "excl e use", "do not print", "do n print", "academic partnership", "evaluation only. created with aspose"]):
                    continue
                if any(frag in b_raw for frag in ["instruc", "rs and", "ents in", "demic p", "ership"]) and any(s.get("size", 0) > 20 for b in cl for l in b.get("lines", []) for s in l.get("spans", [])):
                    continue

                span_fonts = []
                span_sizes = []
                span_colors = []
                span_bolds = []
                span_italics = []

                for b in cl:
                    for line in b.get("lines", []):
                        for s in line.get("spans", []):
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

                # Check if this cluster contains fraction bars
                cl_bars = []
                for fb in frac_bars:
                    if any(b["bbox"][0] - 5 <= fb[0] and fb[2] <= b["bbox"][2] + 5 and b["bbox"][1] - 5 <= fb[1] <= b["bbox"][3] + 5 for b in cl):
                        cl_bars.append(fb)

                if cl_bars:
                    comb_spans = []
                    for b in cl:
                        for l in b.get("lines", []):
                            for s in l.get("spans", []):
                                if s.get("text", "").strip():
                                    comb_spans.append(s)

                    used_span_ids = set()
                    frac_items = []
                    for fb in cl_bars:
                        x0, y_bar, x1, ry0, ry1 = fb
                        num_spans = []
                        den_spans = []
                        for idx, s in enumerate(comb_spans):
                            sb = s["bbox"]
                            overlap = max(0.0, min(x1, sb[2]) - max(x0, sb[0]))
                            span_w = max(1.0, sb[2] - sb[0])
                            if overlap / span_w >= 0.4 or (sb[0] >= x0 - 3 and sb[2] <= x1 + 3):
                                if (y_bar - 22) <= sb[3] <= (y_bar + 2):
                                    num_spans.append((idx, s))
                                elif (y_bar - 2) <= sb[1] <= (y_bar + 22):
                                    den_spans.append((idx, s))

                        if not num_spans and not den_spans:
                            continue

                        num_spans.sort(key=lambda item: item[1]["bbox"][0])
                        den_spans.sort(key=lambda item: item[1]["bbox"][0])

                        def format_tokens(span_list):
                            tokens = []
                            for idx_s, (_, s) in enumerate(span_list):
                                if idx_s > 0 and s.get("size", 11) < span_list[idx_s - 1][1].get("size", 11) * 0.85 and s.get("origin", (0, 0))[1] < span_list[idx_s - 1][1].get("origin", (0, 0))[1] - 2:
                                    tokens.append("^" + s.get("text", "").strip())
                                else:
                                    tokens.append(s.get("text", "").strip())
                            return "".join(tokens).strip()

                        num_txt = format_tokens(num_spans)
                        den_txt = format_tokens(den_spans)
                        # Clean parentheses - only enclose if contains operators (+, -, −)
                        clean_num = f"({num_txt})" if any(c in num_txt for c in "+-\u2212") else num_txt
                        clean_den = f"({den_txt})" if any(c in den_txt for c in "+-\u2212") else den_txt
                        frac_str = f"{clean_num}/{clean_den}" if den_txt else num_txt
                        min_x = min([x0] + [s["bbox"][0] for _, s in num_spans + den_spans])
                        max_x = max([x1] + [s["bbox"][2] for _, s in num_spans + den_spans])
                        frac_items.append((y_bar, min_x, max_x, frac_str))
                        for idx, _ in num_spans + den_spans:
                            used_span_ids.add(idx)

                    comb_items = frac_items + [
                        ((s["bbox"][1] + s["bbox"][3]) / 2.0, s["bbox"][0], s["bbox"][2], s.get("text", "").strip())
                        for idx, s in enumerate(comb_spans)
                        if idx not in used_span_ids
                    ]
                    comb_items.sort(key=lambda it: it[1])
                    line_parts = []
                    for it in comb_items:
                        t = it[3]
                        if line_parts and not line_parts[-1].endswith(" ") and not t.startswith(" "):
                            if t in ["+", "−", "-"] or line_parts[-1] in ["+", "−", "-"]:
                                line_parts.append(" ")
                            elif t in ["1.", "2.", "3.", "4."] or line_parts[-1].endswith("."):
                                line_parts.append("   ")
                            else:
                                line_parts.append(" ")
                        line_parts.append(t)
                    text_clean = "".join(line_parts).strip()
                else:
                    # Regular text block handling
                    lines = [line for b in cl for line in b.get("lines", [])]
                    from app.utils.spacing_engine import merge_tokens as merge_span_tokens
                    structured_lines = []
                    for line in lines:
                        line_spans = [s for s in line.get("spans", []) if s.get("text", "")]
                        if not line_spans:
                            continue
                        span_texts = [s.get("text", "") for s in line_spans]
                        # Compute horizontal coordinate gaps and font sizes between adjacent spans
                        coord_gaps = []
                        font_sizes = []
                        for idx_sp in range(len(line_spans) - 1):
                            s_cur = line_spans[idx_sp]
                            s_next = line_spans[idx_sp + 1]
                            b_cur = s_cur.get("bbox", (0, 0, 0, 0))
                            b_next = s_next.get("bbox", (0, 0, 0, 0))
                            coord_gaps.append(float(b_next[0] - b_cur[2]))
                            font_sizes.append(float(s_cur.get("size", 10.0)))

                        line_str = merge_span_tokens(span_texts, coord_gaps=coord_gaps, font_sizes=font_sizes).strip()
                        if line_str:
                            l_bbox = line.get("bbox", (0, 0, 0, 0))
                            structured_lines.append((float(l_bbox[1]), float(l_bbox[0]), float(l_bbox[2]), line_str))

                    baseline_groups = []
                    for item in sorted(structured_lines, key=lambda i: (i[0], i[1])):
                        y0, x0, x1, l_txt = item
                        matched = False
                        for bg in baseline_groups:
                            if abs(y0 - bg[0][0]) <= 8.0:
                                bg.append(item)
                                matched = True
                                break
                        if not matched:
                            baseline_groups.append([item])

                    merged_block_lines = []
                    for bg in baseline_groups:
                        bg.sort(key=lambda item: item[1])
                        cur_y0, cur_x0, cur_x1, cur_txt = bg[0]
                        for item in bg[1:]:
                            iy0, ix0, ix1, itxt = item
                            gap = ix0 - cur_x1
                            if gap > 180 and not any(w in itxt for w in ("Then", "where", "=")) and not cur_txt.endswith(("+", "-", "=", "*", "/")):
                                merged_block_lines.append((cur_y0, cur_x0, cur_x1, cur_txt))
                                cur_y0, cur_x0, cur_x1, cur_txt = iy0, ix0, ix1, itxt
                            else:
                                cur_x1 = max(cur_x1, ix1)
                                spacer = "   " if gap > 15 else " "
                                cur_txt = f"{cur_txt}{spacer}{itxt}" if not cur_txt.endswith(" ") else f"{cur_txt}{itxt}"
                        merged_block_lines.append((cur_y0, cur_x0, cur_x1, cur_txt))

                    text_clean = "\n".join(item[3] for item in merged_block_lines).strip()
                if not text_clean:
                    continue

                # Filter out background diagonal watermark artifacts
                norm_b = text_clean.lower().replace('\n', ' ')
                if ("exclusive use" in norm_b or "excl e use" in norm_b or "do not print" in norm_b or "do n print" in norm_b) and ("partnership" in norm_b or "ership" in norm_b or "idea" in norm_b):
                    continue

                total_native_chars += len(text_clean)
                cl_x0 = min(float(b["bbox"][0]) for b in cl)
                cl_y0 = min(float(b["bbox"][1]) for b in cl)
                cl_x1 = max(float(b["bbox"][2]) for b in cl)
                cl_y1 = max(float(b["bbox"][3]) for b in cl)
                bbox = [cl_x0, cl_y0, cl_x1, cl_y1]

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

                    # Generate text representation for downstream text extraction / originality check
                    table_text_lines = []
                    if headers and any(h.strip() for h in headers):
                        table_text_lines.append(" | ".join(h.strip() for h in headers if h.strip()))
                    for r in rows:
                        row_vals = [c.strip() for c in r if c and c.strip()]
                        if row_vals:
                            table_text_lines.append(" | ".join(row_vals))
                    table_full_text = "\n".join(table_text_lines).strip()

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
                        text=table_full_text,
                        headers=headers,
                        rows=rows,
                        confidence=1.0
                    ))
                    elem_counter += 1
                    stats.tables_count += 1
            except Exception as ex_tab:
                logger.debug(f"Native table extraction note: {ex_tab}")

            # Step 3 — Extract All PDF Images (Normal & MathType images) into original_images/
            orig_images_dir = os.path.join(temp_dir, "original_images")
            os.makedirs(orig_images_dir, exist_ok=True)
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
                    img_save_path = os.path.join(orig_images_dir, img_filename)
                    if image_bytes:
                        with open(img_save_path, "wb") as f:
                            f.write(image_bytes)
                        # Also maintain root copy for backward compatibility
                        root_copy_path = os.path.join(temp_dir, img_filename)
                        if not os.path.exists(root_copy_path):
                            with open(root_copy_path, "wb") as f_root:
                                f_root.write(image_bytes)
                        img_url = f"/api/image/{job_id}/original_images/{img_filename}"
                except Exception as ex:
                    logger.warning(f"Could not extract image bytes for xref {xref}: {ex}")

                for rect_info in img_rects:
                    img_bbox = [float(rect_info.x0), float(rect_info.y0), float(rect_info.x1), float(rect_info.y1)]
                    img_id = f"img_p{page_num}_{img_idx+1}"
                    rw = float(rect_info.width)
                    rh = float(rect_info.height)

                    # Skip full-page background scans or massive page-spanning images (> 65% width AND height, or > 80% width, or > 80% height)
                    # so they do not cover or suppress genuine discrete child figures, flags, photos, and drawings
                    if (rw >= 0.65 * page_width and rh >= 0.65 * page_height) or (rw >= 0.80 * page_width and rh >= 0.40 * page_height) or (rh >= 0.80 * page_height and rw >= 0.40 * page_width):
                        continue
                    # Also skip 1-bit monochrome (bpc=1) container/column scan artifacts spanning large blocks (w > 120 and h > 150)
                    # These are text-rendering or background scan masks, NOT genuine individual figures or photos
                    if img_info[4] == 1 and (rw >= 140.0 and rh >= 140.0):
                        continue

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
                        tag="Image",
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
                                elif max(w_im, h_im) < 700:
                                    # For medium graphs/charts, a clean 1.5x Lanczos upscale resolves fine axis labels (like '0' at coordinate origins)
                                    scale_factor = 1.5
                                    scale_m = 1.5
                                    upscaled_im = test_im.resize((int(w_im * scale_factor), int(h_im * scale_factor)), Image.Resampling.LANCZOS)
                                    upscaled_path = s_img["path"] + "_upscaled.png"
                                    upscaled_im.save(upscaled_path)
                                    img_path_for_ocr = upscaled_path
                        except Exception:
                            img_path_for_ocr = s_img["path"]

                        crop_results = self.ocr_engine.run_ocr(img_path_for_ocr, page_num=page_num)
                        crop_results = assemble_vertical_fractions(crop_results)
                        img_bbox = s_img["bbox"]
                        iw = max(1.0, img_bbox[2] - img_bbox[0])
                        ih = max(1.0, img_bbox[3] - img_bbox[1])

                        # Determine actual dimensions of the image supplied to OCR engine
                        try:
                            with Image.open(img_path_for_ocr) as ocr_im:
                                actual_w, actual_h = ocr_im.size
                        except Exception:
                            actual_w = max(1, int(s_img["width"]))
                            actual_h = max(1, int(s_img["height"]))

                        actual_w = max(1.0, float(actual_w))
                        actual_h = max(1.0, float(actual_h))

                        for crop_res in crop_results:
                            crop_text = crop_res.get("text", "").strip()
                            if not crop_text:
                                continue
                            c_bbox = crop_res.get("bbox", [0, 0, 0, 0])
                            crop_conf = crop_res.get("confidence")

                            norm_x0 = max(0.0, min(1.0, c_bbox[0] / actual_w))
                            norm_y0 = max(0.0, min(1.0, c_bbox[1] / actual_h))
                            norm_x1 = max(norm_x0, min(1.0, c_bbox[2] / actual_w))
                            norm_y1 = max(norm_y0, min(1.0, c_bbox[3] / actual_h))

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

                            # Save the extracted snippet into extracted_images/ directory
                            extracted_images_dir = os.path.join(temp_dir, "extracted_images")
                            os.makedirs(extracted_images_dir, exist_ok=True)
                            crop_elem_filename = f"extracted_p{page_num}_{elem_counter}.png"
                            crop_save_path = os.path.join(extracted_images_dir, crop_elem_filename)
                            crop_img_url = f"/api/image/{job_id}/extracted_images/{crop_elem_filename}"

                            try:
                                with Image.open(s_img["path"]) as orig_im:
                                    cw, ch = orig_im.size
                                    c_x0 = max(0, int(norm_x0 * cw))
                                    c_y0 = max(0, int(norm_y0 * ch))
                                    c_x1 = min(cw, max(c_x0 + 1, int(norm_x1 * cw)))
                                    c_y1 = min(ch, max(c_y0 + 1, int(norm_y1 * ch)))
                                    snippet = orig_im.crop((c_x0, c_y0, c_x1, c_y1))
                                    snippet.save(crop_save_path)
                            except Exception:
                                crop_img_url = None

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
                                bbox=mapped_bbox,
                                image_id=f"ext_img_p{page_num}_{elem_counter}",
                                image_path=crop_img_url
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
                        
                        # If PP-Structure misclassifies a large text region/column as a 'figure', check its text payload:
                        # Real figures/photos do NOT have multi-line paragraphs. If it contains extensive text, treat as layout text block.
                        struct_text = (struct_res.get("text") or "").strip()
                        is_genuine_fig = (st_type == "figure")
                        if is_genuine_fig and (len(struct_text.split()) >= 15 or len(struct_text) >= 80):
                            is_genuine_fig = False
                            st_type = "text"

                        if st_type in ("equation", "formula"):
                            st_type = "formula"
                            stats.formulas_count += 1
                        elif st_type == "table":
                            stats.tables_count += 1
                        elif is_genuine_fig:
                            stats.images_count += 1
                        else:
                            stats.pp_structure_regions += 1

                        pp_classification = TagClassifier.classify_element(
                            text=struct_res.get("text"),
                            bbox=scaled_bbox,
                            is_table=(st_type == "table"),
                            is_image=is_genuine_fig,
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

            # Step 5b — Comprehensive Non-Text Visual Element Discovery (Figures, Flags, Lines, Decorative Bars)
            try:
                from app.layout.visual_detector import detect_visual_elements_from_page_image
                known_text_boxes = [e.bbox for e in elements if e.text and e.text.strip() and e.bbox]
                if os.path.exists(page_img_path):
                    detected_visuals = detect_visual_elements_from_page_image(
                        page_img_path=page_img_path,
                        page_rect=rect,
                        known_text_bboxes=known_text_boxes,
                        render_dpi=self.render_dpi
                    )
                    for vis in detected_visuals:
                        vb = vis["bbox"]
                        # Check if this visual element is already accounted for by an existing native/image element.
                        # Exclude full-page scans or massive column container images so distinct sub-elements (photos, flags) are not suppressed.
                        already_exists = False
                        for e_cur in elements:
                            if e_cur.type in ("image", "figure", "drawing") and e_cur.bbox:
                                cb = e_cur.bbox
                                cb_w = float(cb[2] - cb[0])
                                cb_h = float(cb[3] - cb[1])
                                # A visual sub-element (photo, icon, flag) should ONLY be marked as already existing
                                # if the matching element has a comparable size (i.e. not a container holding it)
                                overlap_w = max(0.0, min(vb[2], cb[2]) - max(vb[0], cb[0]))
                                overlap_h = max(0.0, min(vb[3], cb[3]) - max(vb[1], cb[1]))
                                overlap_area = overlap_w * overlap_h
                                vb_area = (vb[2] - vb[0]) * (vb[3] - vb[1])
                                cb_area = cb_w * cb_h
                                # If existing element is more than 2.5x larger than this visual sub-element,
                                # it is a container box/card, NOT the same element!
                                if cb_area > 2.5 * vb_area:
                                    continue
                                if overlap_area / max(1.0, vb_area) >= 0.60:
                                    already_exists = True
                                    break
                        if already_exists:
                            continue

                        v_type = vis["type"]
                        v_subtype = vis.get("subtype", "figure")
                        v_tag = "Figure"

                        # Crop and generate high-fidelity visual preview for this element
                        vis_img_url = None
                        vis_img_id = f"vis_{v_subtype}_p{page_num}_{elem_counter}"
                        try:
                            extracted_images_dir = os.path.join(temp_dir, "extracted_images")
                            os.makedirs(extracted_images_dir, exist_ok=True)
                            vis_filename = f"{vis_img_id}.png"
                            vis_save_path = os.path.join(extracted_images_dir, vis_filename)
                            
                            scale_pt_to_px = self.render_dpi / 72.0
                            crop_x0 = max(0, int(vb[0] * scale_pt_to_px))
                            crop_y0 = max(0, int(vb[1] * scale_pt_to_px))
                            crop_x1 = max(crop_x0 + 1, int(vb[2] * scale_pt_to_px))
                            crop_y1 = max(crop_y0 + 1, int(vb[3] * scale_pt_to_px))
                            
                            with Image.open(page_img_path) as full_page_im:
                                c_im = full_page_im.crop((crop_x0, crop_y0, min(full_page_im.width, crop_x1), min(full_page_im.height, crop_y1)))
                                c_im.save(vis_save_path)
                            vis_img_url = f"/api/image/{job_id}/extracted_images/{vis_filename}"
                        except Exception as ex_crop:
                            logger.debug(f"Visual element crop note: {ex_crop}")

                        elem_id = f"vis_elem_p{page_num}_{elem_counter}"
                        elements.append(ExtractedElement(
                            id=elem_id,
                            page=page_num,
                            type=v_type,
                            content_type=v_type,
                            tag=v_tag,
                            is_tagged=False,
                            tag_source="visual_detector",
                            parameters={
                                "content_type": v_type,
                                "subtype": v_subtype,
                                "tag": v_tag,
                                "bbox": vb,
                                "width": vis["width"],
                                "height": vis["height"],
                                "object_path": f"/Document/Page[{page_num}]/{v_tag}[{elem_counter}]",
                                "confidence": 1.0
                            },
                            source="visual_detector",
                            bbox=vb,
                            confidence=1.0,
                            image_id=vis_img_id,
                            image_path=vis_img_url,
                            width=int(vis["width"]),
                            height=int(vis["height"])
                        ))
                        elem_counter += 1
                        stats.images_count += 1
            except Exception as ex_vis:
                logger.debug(f"Visual element detection note: {ex_vis}")

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

        # Step 9 — Non-Text Object Inventory Validation & Path Verification
        # Validates that every detected visual element has valid bounding box coordinates, a page mapping,
        # and a usable object reference/path for the accessibility remediation workflow.
        unresolved_visual_objects = []
        for elem in all_extracted_elements:
            if elem.type in ("image", "figure", "drawing"):
                has_bbox = bool(elem.bbox and len(elem.bbox) >= 4 and elem.bbox[2] > elem.bbox[0] and elem.bbox[3] > elem.bbox[1])
                has_path = bool(elem.parameters.get("object_path") or elem.image_path or elem.image_id)
                has_page = bool(elem.page and elem.page >= 1)
                
                if not (has_bbox and has_path and has_page):
                    elem.parameters["validation_status"] = "Needs Review"
                    elem.parameters["validation_error"] = "Missing coordinates, object path, or page mapping"
                    unresolved_visual_objects.append({
                        "id": elem.id,
                        "page": elem.page,
                        "type": elem.type,
                        "error": "Missing valid bounding box or object reference path"
                    })
                else:
                    elem.parameters["validation_status"] = "Validated"
                    if "object_path" not in elem.parameters:
                        elem.parameters["object_path"] = f"/Document/Page[{elem.page}]/{elem.tag or 'Figure'}[{elem.id}]"

        tagging_summary = TagClassifier.build_tagging_summary(all_extracted_elements, doc_is_tagged=doc_is_tagged)
        if unresolved_visual_objects:
            tagging_summary["unresolved_visual_objects"] = unresolved_visual_objects

        return {
            "pages": pages_data,
            "statistics": stats,
            "is_tagged_document": doc_is_tagged,
            "tagging_summary": tagging_summary,
            "unresolved_visual_objects": unresolved_visual_objects
        }
