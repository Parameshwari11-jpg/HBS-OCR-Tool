import os
import re
import uuid
import logging
from typing import List, Dict, Any, Optional, Callable, Tuple
import pymupdf  # PyMuPDF

from app.originality.models import (
    PageOriginalityResult,
    VerificationType,
    MismatchItem,
    LineDiffItem,
)
from app.originality.normalizer import TextNormalizer
from app.originality.diff_engine import DiffEngine
from app.originality.accuracy import AccuracyCalculator

logger = logging.getLogger("pdf_checker")


class PDFOriginalityChecker:
    """
    Page-by-page verification for PDF documents against extracted text.
    Handles native text, multi-column layouts, headers/footers, tables,
    and falls back to OCR for image/scanned pages.
    """

    def __init__(self, ocr_processor: Optional[Any] = None):
        self.ocr_processor = ocr_processor

    def check_pdf(
        self,
        pdf_path: str,
        extracted_text: str,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
        docx_source_path: Optional[str] = None,
        job_id: Optional[str] = None
    ) -> List[PageOriginalityResult]:
        """
        Processes PDF page-by-page and compares against extracted text.
        """
        doc = pymupdf.open(pdf_path)
        total_pages = len(doc)
        page_results: List[PageOriginalityResult] = []

        # Parse extracted text by page delimiters if available
        extracted_pages_map = self._split_extracted_text_by_pages(extracted_text, total_pages)

        ole_texts: Dict[str, str] = {}
        if docx_source_path and os.path.exists(docx_source_path):
            try:
                from app.extractors.mtef_decoder import extract_docx_mathtype_equations
                ole_texts = extract_docx_mathtype_equations(docx_source_path)
            except Exception as e_ole:
                logger.warning(f"Could not extract MathType equations from {docx_source_path}: {e_ole}")

        job_result = None
        if job_id:
            try:
                from app.services.job_service import job_service
                job_result = job_service.get_result(job_id)
            except Exception as ex_job:
                logger.debug(f"Could not load job_result for {job_id}: {ex_job}")

        for page_idx in range(total_pages):
            page_num = page_idx + 1
            if progress_callback:
                progress_callback(f"Processing Page {page_num} of {total_pages}...", page_num, total_pages)

            try:
                page = doc[page_idx]

                # 1. Extract reference text from original PDF page
                ref_text = ""
                ver_type = VerificationType.TEXT_BASED
                confidence = None

                if job_result and page_idx < len(job_result.pages):
                    from app.utils.normalization import is_ui_artifact, clean_ocr_text
                    p_data = job_result.pages[page_idx]
                    valid_elems = [e for e in p_data.elements if not e.possible_duplicate and e.type not in ("image", "figure")]
                    sorted_elems = sorted(valid_elems, key=lambda e: (
                        e.reading_order if e.reading_order is not None and e.reading_order > 0 else 99999,
                        e.bbox[1] if e.bbox else 99999,
                        e.bbox[0] if e.bbox else 99999
                    ))
                    elem_lines = []
                    for elem in sorted_elems:
                        if elem.text and elem.text.strip():
                            if is_ui_artifact(elem.text, elem.bbox, confidence=elem.confidence):
                                continue
                            cleaned_txt = clean_ocr_text(elem.text) if elem.source == "ocr" else elem.text.strip()
                            if cleaned_txt and not is_ui_artifact(cleaned_txt, elem.bbox, confidence=elem.confidence):
                                elem_lines.append(cleaned_txt)
                    ref_text = "\n".join(elem_lines)
                    ver_type = VerificationType.TEXT_BASED

                line_positions = []
                if not ref_text:
                    ref_text, ver_type, confidence, line_positions = self._extract_page_reference_text(page, page_num, ole_texts=ole_texts)

                # 2. Get extracted text for this page
                ext_page_text = extracted_pages_map.get(page_num, "")

                # 3. Normalize lines for comparison
                orig_lines = TextNormalizer.get_lines(ref_text)
                ext_lines = TextNormalizer.get_lines(ext_page_text)

                orig_words = TextNormalizer.extract_words(ref_text)
                ext_words = TextNormalizer.extract_words(ext_page_text)

                # 4. Compare lines, words, numbers, and characters
                line_diffs, mismatches = DiffEngine.compare_page_lines(
                    orig_lines=orig_lines,
                    ext_lines=ext_lines,
                    page_num=page_num,
                    confidence=confidence
                )

                # 5. Compute page accuracy & status
                accuracy, status = AccuracyCalculator.calculate_page_accuracy(
                    orig_words=orig_words,
                    ext_words=ext_words,
                    mismatches=mismatches
                )

                page_results.append(PageOriginalityResult(
                    page=page_num,
                    orig_word_count=len(orig_words),
                    extracted_word_count=len(ext_words),
                    orig_char_count=sum(len(c) for c in orig_words),
                    extracted_char_count=sum(len(c) for c in ext_words),
                    accuracy=accuracy,
                    status=status,
                    verification_type=ver_type,
                    mismatches=mismatches,
                    orig_lines=orig_lines,
                    extracted_lines=ext_lines,
                    line_positions=line_positions,
                    line_diffs=line_diffs
                ))

            except Exception as e:
                logger.error(f"Error checking page {page_num}: {e}", exc_info=True)
                # Graceful fallback: record error for this page without aborting entire process
                page_results.append(PageOriginalityResult(
                    page=page_num,
                    orig_word_count=0,
                    extracted_word_count=0,
                    orig_char_count=0,
                    extracted_char_count=0,
                    accuracy=0.0,
                    status=AccuracyCalculator.calculate_page_accuracy([], [], [])[1],
                    verification_type=VerificationType.TEXT_BASED,
                    mismatches=[],
                    orig_lines=[],
                    extracted_lines=[],
                    line_diffs=[]
                ))

        doc.close()
        return page_results

    def _extract_page_reference_text(
        self,
        page: pymupdf.Page,
        page_num: int,
        ole_texts: Optional[Dict[str, str]] = None
    ) -> Tuple[str, VerificationType, Optional[float]]:
        """
        Extracts original reference text from a PDF page using PyMuPDF reading order,
        or triggers OCR if the page is scanned/image-only.
        """
        # 1. Native text extraction via baseline-aligned reading order
        text_dict = page.get_text("dict")
        blocks = text_dict.get("blocks", [])

        # Collect valid text blocks, preserving block cohesion (prevents multi-column interleaving)
        valid_blocks = []
        for b in blocks:
            if b.get("type") == 0:
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

                from app.utils.spacing_engine import merge_tokens as merge_span_tokens
                structured_lines = []
                for l in b.get("lines", []):
                    line_spans = [s for s in l.get("spans", []) if s.get("text", "")]
                    if not line_spans:
                        continue
                    span_texts = [s.get("text", "") for s in line_spans]
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
                        l_bbox = l.get("bbox", (0, 0, 0, 0))
                        structured_lines.append((float(l_bbox[1]), float(l_bbox[0]), float(l_bbox[2]), line_str))

                # Group lines by baseline (y0/yc within 8pt) & pair vertical math fractions (num/den)
                items = sorted(structured_lines, key=lambda i: (i[0], i[1]))
                used_indices = set()
                frac_assembled = []

                for i in range(len(items)):
                    if i in used_indices:
                        continue
                    y0_top, x0_top, x1_top, txt_top = items[i]
                    clean_top = txt_top.strip()
                    is_top_frac = len(clean_top) <= 12 and not any(c in clean_top for c in [':', ';', ',', '!', '?', '"', '=', '+'])

                    best_j = None
                    best_dist = 999.0

                    if is_top_frac:
                        cx_top = (x0_top + x1_top) / 2.0
                        w_top = max(1.0, x1_top - x0_top)

                        for j in range(i + 1, len(items)):
                            if j in used_indices:
                                continue
                            y0_bot, x0_bot, x1_bot, txt_bot = items[j]
                            clean_bot = txt_bot.strip()
                            is_bot_frac = len(clean_bot) <= 12 and not any(c in clean_bot for c in [':', ';', ',', '!', '?', '"', '=', '+'])

                            if not is_bot_frac:
                                continue

                            v_gap = y0_bot - y0_top
                            if 2 <= v_gap <= 26:
                                cx_bot = (x0_bot + x1_bot) / 2.0
                                w_bot = max(1.0, x1_bot - x0_bot)
                                cx_diff = abs(cx_top - cx_bot)
                                h_overlap = max(0.0, min(x1_top, x1_bot) - max(x0_top, x0_bot))
                                min_w = min(w_top, w_bot)

                                if (h_overlap > 0.25 * min_w or cx_diff <= max(10.0, 0.5 * max(w_top, w_bot))) and cx_diff < best_dist:
                                    best_j = j
                                    best_dist = cx_diff

                    if best_j is not None:
                        j = best_j
                        y0_bot, x0_bot, x1_bot, txt_bot = items[j]
                        clean_bot = txt_bot.strip()
                        frac_txt = f"{clean_top}/{clean_bot}"
                        new_y0 = (y0_top + y0_bot) / 2.0
                        new_x0 = min(x0_top, x0_bot)
                        new_x1 = max(x1_top, x1_bot)
                        frac_assembled.append((new_y0, new_x0, new_x1, frac_txt))
                        used_indices.add(i)
                        used_indices.add(j)
                    else:
                        frac_assembled.append(items[i])
                        used_indices.add(i)

                baseline_groups = []
                for item in sorted(frac_assembled, key=lambda i: (i[0], i[1])):
                    y0, x0, x1, l_txt = item
                    matched = False
                    for bg in baseline_groups:
                        if abs(y0 - bg[0][0]) <= 8.0:
                            bg.append(item)
                            matched = True
                            break
                    if not matched:
                        baseline_groups.append([item])

                block_lines = []
                for bg in baseline_groups:
                    bg.sort(key=lambda item: item[1]) # Sort left-to-right
                    cur_y0, cur_x0, cur_x1, cur_txt = bg[0]
                    for item in bg[1:]:
                        iy0, ix0, ix1, itxt = item
                        if (ix0 - cur_x1) > 30 and not any(w in itxt for w in ('Then', 'where', '=')) and not cur_txt.endswith(('+', '-', '=', '*', '/')):
                            block_lines.append(cur_txt)
                            cur_y0, cur_x0, cur_x1, cur_txt = iy0, ix0, ix1, itxt
                        else:
                            cur_x1 = max(cur_x1, ix1)
                            cur_txt = f"{cur_txt} {itxt}" if not cur_txt.endswith(' ') else f"{cur_txt}{itxt}"
                    block_lines.append(cur_txt)

                if block_lines:
                    bbox = b.get("bbox", (0, 0, 0, 0))
                    valid_blocks.append((float(bbox[1]), float(bbox[3]), float(bbox[0]), float(bbox[2]), block_lines))

        # 1b. Embedded image OCR extraction (for screenshots, forms, diagrams)
        # Each OCR result is appended as a single-line block to be merged into the visual-line grid below
        ocr_segment_blocks = []  # list of (y0, y1, x0, x1, [line_str])
        if not self.ocr_processor:
            try:
                from app.services.extraction_service import extraction_service
                self.ocr_processor = extraction_service.paddle_ocr
            except Exception as ex:
                logger.warning(f"Could not load paddle_ocr: {ex}")

        image_list = page.get_images(full=True)
        if image_list and self.ocr_processor:
            from app.utils.normalization import clean_ocr_text, is_ui_artifact
            doc_ref = page.parent
            for idx, img_info in enumerate(image_list):
                xref = img_info[0]
                rects = page.get_image_rects(xref)
                if not rects:
                    continue
                try:
                    base_img = doc_ref.extract_image(xref)
                    img_bytes = base_img.get("image")
                    img_ext = base_img.get("ext", "png")
                    img_w = base_img.get("width", 1)
                    img_h = base_img.get("height", 1)
                    if not img_bytes:
                        continue
                    # Skip tiny toolbar / button / bullet icons — they cannot contain meaningful text
                    if img_w < 28 or img_h < 20:
                        continue
                    temp_crop_path = f"temp_crop_p{page_num}_{idx}_{uuid.uuid4().hex[:6]}.{img_ext}"
                    with open(temp_crop_path, "wb") as f_crop:
                        f_crop.write(img_bytes)

                    try:
                        crop_results = []
                        if hasattr(self.ocr_processor, 'run_ocr'):
                            crop_results = self.ocr_processor.run_ocr(temp_crop_path, page_num=page_num)
                        elif hasattr(self.ocr_processor, 'process_image'):
                            crop_results = self.ocr_processor.process_image(temp_crop_path, page_num=page_num)

                        for rect_info in rects:
                            img_bbox = [float(rect_info.x0), float(rect_info.y0), float(rect_info.x1), float(rect_info.y1)]
                            iw = max(1.0, img_bbox[2] - img_bbox[0])
                            ih = max(1.0, img_bbox[3] - img_bbox[1])
                            crop_w = max(1.0, float(img_w))
                            crop_h = max(1.0, float(img_h))

                            for cr in crop_results:
                                c_text = cr.get("text", "").strip()
                                if not c_text:
                                    continue
                                c_bbox = cr.get("bbox", [0, 0, 0, 0])
                                c_conf = cr.get("confidence")

                                mapped_y0 = img_bbox[1] + (c_bbox[1] / crop_h) * ih
                                mapped_y1 = img_bbox[1] + (c_bbox[3] / crop_h) * ih
                                mapped_x0 = img_bbox[0] + (c_bbox[0] / crop_w) * iw
                                mapped_x1 = img_bbox[0] + (c_bbox[2] / crop_w) * iw
                                mapped_bbox = [mapped_x0, mapped_y0, mapped_x1, mapped_y1]

                                if is_ui_artifact(c_text, mapped_bbox, confidence=c_conf):
                                    continue
                                c_text = clean_ocr_text(c_text)
                                if not c_text or is_ui_artifact(c_text, mapped_bbox, confidence=c_conf):
                                    continue
                                # Append as a single-line block for the block-cohesion grid
                                ocr_segment_blocks.append(
                                    (mapped_y0, mapped_y1, mapped_x0, mapped_x1, [c_text])
                                )
                    finally:
                        if os.path.exists(temp_crop_path):
                            try:
                                os.remove(temp_crop_path)
                            except Exception:
                                pass
                except Exception as ex_img:
                    logger.debug(f"Image extraction note for xref {xref}: {ex_img}")

        # Merge OCR single-line blocks into the block list
        all_blocks = valid_blocks + ocr_segment_blocks

        # --- Block-Cohesion Grid: group blocks into visual lines, then sort left-to-right ---
        # This prevents multi-column tables from interleaving lines across columns
        grouped = []
        for y0, y1, x0, x1, lines in sorted(all_blocks, key=lambda b: (b[0], b[2])):
            yc = (y0 + y1) / 2.0
            h = max(1.0, y1 - y0)
            placed = False
            for g in grouped:
                ref_yc = sum((item[0] + item[1]) / 2.0 for item in g) / len(g)
                ref_h = sum(max(1.0, item[1] - item[0]) for item in g) / len(g)
                if abs(yc - ref_yc) <= max(5.0, 0.45 * min(h, ref_h)):
                    g.append((y0, y1, x0, x1, lines))
                    placed = True
                    break
            if not placed:
                grouped.append([(y0, y1, x0, x1, lines)])

        # Sort visual-line groups top-to-bottom by average vertical center
        grouped.sort(key=lambda g: sum((item[0] + item[1]) / 2.0 for item in g) / len(g))

        extracted_lines = []
        line_positions = []
        page_h = float(page.rect.height) if (page and hasattr(page, 'rect') and page.rect.height > 0) else 792.0
        page_w = float(page.rect.width) if (page and hasattr(page, 'rect') and page.rect.width > 0) else 612.0

        for g in grouped:
            g.sort(key=lambda item: item[2])
            for y0, y1, x0, x1, block_lines in g:
                top_pct = round((y0 / page_h) * 100.0, 2)
                h_pct = round((max(12.0, y1 - y0) / page_h) * 100.0, 2)
                left_pct = round((x0 / page_w) * 100.0, 2)
                w_pct = round(((x1 - x0) / page_w) * 100.0, 2)
                for line_str in block_lines:
                    norm_line = TextNormalizer.normalize_line(line_str)
                    if norm_line:
                        extracted_lines.append(norm_line)
                        line_positions.append({
                            "top": top_pct,
                            "height": h_pct,
                            "left": left_pct,
                            "width": w_pct
                        })

        # 2. Enrich with decoded MathType/OMML formulas if available
        if ole_texts:
            try:
                from app.extractors.xml_extractor import extract_docx_xml_content
                _math_para_cache_key = id(ole_texts)
                if not hasattr(self, '_math_para_cache') or self._math_para_cache.get('key') != _math_para_cache_key:
                    self._math_para_cache = {'key': _math_para_cache_key, 'lines': []}
                    import re as _re
                    numbered_eqs = sorted(
                        [(int(_re.search(r'(\d+)\.bin$', k).group(1)), v)
                         for k, v in ole_texts.items()
                         if _re.search(r'(\d+)\.bin$', k) and v],
                        key=lambda x: x[0]
                    )
                    self._math_para_cache['eqs'] = {n: v for n, v in numbered_eqs}
            except Exception as ex_xml:
                logger.debug(f"MathType XML enrichment note: {ex_xml}")

        native_text = "\n".join(extracted_lines)
        word_count = len(native_text.split())

        # If page has substantial text (>= 5 words), use native text-based reference
        if word_count >= 5:
            return native_text, VerificationType.TEXT_BASED, None, line_positions

        # Check if page has images / scanned content or lacks native text
        image_blocks = [b for b in blocks if b.get("type") == 1]
        has_images = len(image_blocks) > 0 or len(page.get_images()) > 0
        raw_native = page.get_text().strip()
        if (has_images or word_count < 5) and len(raw_native) < 15:
            if not self.ocr_processor:
                try:
                    from app.services.extraction_service import extraction_service
                    self.ocr_processor = extraction_service.paddle_ocr
                except Exception as ex:
                    logger.warning(f"Could not load paddle_ocr: {ex}")

            if self.ocr_processor:
                try:
                    logger.info(f"Page {page_num} is image-dominant or scanned. Performing OCR verification...")
                    # Render high-DPI pixmap for OCR
                    pix = page.get_pixmap(dpi=150)
                    temp_img_path = f"temp_page_{page_num}_ocr_{uuid.uuid4().hex[:6]}.png"
                    pix.save(temp_img_path)

                    ocr_text = ""
                    confidence = None
                    try:
                        if hasattr(self.ocr_processor, 'run_ocr'):
                            ocr_results = self.ocr_processor.run_ocr(temp_img_path, page_num=page_num)
                        elif hasattr(self.ocr_processor, 'process_image'):
                            ocr_results = self.ocr_processor.process_image(temp_img_path, page_num=page_num)
                        else:
                            ocr_results = []
                        lines = [r.get("text", "") for r in ocr_results if r.get("text")]
                        confs = [r.get("confidence", 0.9) for r in ocr_results if r.get("confidence")]
                        ocr_text = "\n".join(lines)
                        confidence = sum(confs) / len(confs) if confs else 0.85
                    finally:
                        if os.path.exists(temp_img_path):
                            try:
                                os.remove(temp_img_path)
                            except Exception:
                                pass

                    if ocr_text.strip():
                        return ocr_text, VerificationType.OCR_BASED, confidence, line_positions
                except Exception as e:
                    logger.warning(f"OCR fallback failed on page {page_num}: {e}")

        # Return whatever native text exists
        return native_text, VerificationType.TEXT_BASED, None, line_positions

    def _split_extracted_text_by_pages(
        self,
        extracted_text: str,
        total_pages: int
    ) -> Dict[int, str]:
        """
        Parses extracted text into per-page mapping using standard page delimiters
        ('--- Page X ---') or partitions proportionally.
        """
        pages_map: Dict[int, str] = {}
        if not extracted_text:
            return pages_map

        regex = re.compile(r'---\s*Page\s*(\d+)\s*---', re.IGNORECASE)
        splits = regex.split(extracted_text)

        # If delimiters like '--- Page 1 ---' are found
        if len(splits) > 1:
            # splits structure: [preamble, pNum1, text1, pNum2, text2, ...]
            for i in range(1, len(splits), 2):
                try:
                    p_num = int(splits[i])
                    p_text = splits[i + 1].strip() if i + 1 < len(splits) else ""
                    pages_map[p_num] = p_text
                except (ValueError, IndexError):
                    pass

        # If page map is populated, return it
        if pages_map:
            return pages_map

        # Fallback: if document has 1 page or no delimiters, map all text to page 1
        if total_pages <= 1:
            pages_map[1] = extracted_text.strip()
            return pages_map

        # Multi-page fallback without page markers: partition by form feeds or line blocks
        lines = extracted_text.strip().split('\n')
        lines_per_page = max(1, len(lines) // total_pages)
        for p in range(1, total_pages + 1):
            start = (p - 1) * lines_per_page
            end = p * lines_per_page if p < total_pages else len(lines)
            pages_map[p] = "\n".join(lines[start:end]).strip()

        return pages_map
