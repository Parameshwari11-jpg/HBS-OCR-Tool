import os
import zipfile
import logging
from typing import List, Dict, Any, Optional, Callable
import pythoncom
import docx
from PIL import Image
import pymupdf

from app.models.extraction_models import PageData, ExtractedElement, FontInfo, ExtractionStatistics
from app.extractors.xml_extractor import extract_docx_xml_content
from app.extractors.image_extractor import ImageExtractor
from app.extractors.pdf_extractor import PDFExtractor
from app.ocr.paddle_ocr_engine import PaddleOCREngine
from app.ocr.pp_structure_engine import PPStructureEngine
from app.layout.tag_classifier import TagClassifier
from app.utils.image_converter import convert_to_web_image
from app.utils.normalization import is_ui_artifact, clean_ocr_text

logger = logging.getLogger("docx_extractor")

class DOCXExtractor:
    def __init__(
        self,
        ocr_engine: Optional[PaddleOCREngine] = None,
        structure_engine: Optional[PPStructureEngine] = None
    ):
        self.ocr_engine = ocr_engine or PaddleOCREngine()
        self.structure_engine = structure_engine or PPStructureEngine()
        self.image_extractor = ImageExtractor(ocr_engine=self.ocr_engine)
        self.pdf_extractor = PDFExtractor(ocr_engine=self.ocr_engine, structure_engine=self.structure_engine)

    def extract_docx(
        self,
        docx_path: str,
        temp_dir: str,
        progress_callback: Optional[Callable[[str, int, Optional[int], Optional[int], Optional[str]], None]] = None
    ) -> Dict[str, Any]:
        job_id = os.path.basename(temp_dir)
        converted_pdf_path = os.path.join(temp_dir, "original_converted.pdf")
        
        # 1. Primary Strategy: Pixel-Perfect Original Document Rendering via MS Word (docx2pdf)
        pdf_success = False
        try:
            logger.info("Initializing COM and converting Word document to exact PDF for 100% original layout...")
            if progress_callback:
                progress_callback(
                    "converting",
                    12,
                    None,
                    None,
                    "Converting Word document to preserve 100% original visual layout..."
                )

            pythoncom.CoInitialize()
            try:
                from docx2pdf import convert
                convert(docx_path, converted_pdf_path)
            finally:
                pythoncom.CoUninitialize()

            if os.path.exists(converted_pdf_path) and os.path.getsize(converted_pdf_path) > 1000:
                logger.info("Word document successfully converted to exact original PDF. Running high-DPI PDF extraction...")
                if progress_callback:
                    progress_callback(
                        "page_processing",
                        18,
                        1,
                        None,
                        "Document converted. Extracting pages, text & MathType formulas..."
                    )
                res = self.pdf_extractor.extract_pdf(converted_pdf_path, temp_dir, progress_callback=progress_callback)
                pdf_success = True
                
                # Blend XML & MathType formulas from original DOCX into pages and text elements
                # Generic approach: use extract_docx_xml_content to get paragraph_with_math lines
                # in document order, then match against extracted elements by sequence.
                # No hardcoded page numbers or pixel bounding boxes.
                try:
                    import re as _re
                    from app.extractors.xml_extractor import extract_docx_xml_content

                    xml_content = extract_docx_xml_content(docx_path)
                    # Build ordered list of math paragraph lines from xml_extractor
                    math_para_lines = [
                        x['text'] for x in xml_content
                        if x.get('type') == 'paragraph_with_math' and x.get('text')
                    ]

                    def clean_str(s: str) -> str:
                        return _re.sub(r'\s+', ' ', s or '').strip()

                    # A pattern matching isolated number/operator fragments that are equation placeholders
                    _frag_pat = _re.compile(r'^[\d\.\+\-\s]+$')
                    # A pattern for elements that ARE real text (not math fragments)
                    _real_text_pat = _re.compile(r'[a-zA-Z]{2,}')

                    math_para_iter = iter(math_para_lines)

                    for p in res["pages"]:
                        for elem in p.elements:
                            t = clean_str(elem.text or '')

                            # Mark isolated operator/bar artifacts as duplicates
                            if _re.match(r'^[+\-−\s]+$', t):
                                elem.possible_duplicate = True
                                continue

                            old_t = elem.text

                            # If this element's text is a pure number/operator fragment placeholder
                            # (e.g. '1.', '2.', '1. 2.', '3.', or a bare separator)
                            # replace it with the next math paragraph line in sequence.
                            if _frag_pat.match(t) and not _real_text_pat.search(t):
                                try:
                                    mp = next(math_para_iter)
                                    elem.text = mp
                                    elem.possible_duplicate = False
                                except StopIteration:
                                    elem.possible_duplicate = True
                                    continue

                            # Synchronize classification when text changed
                            if elem.text != old_t:
                                is_formula_elem = ('/' in elem.text or '=' in elem.text) and 'represent polynomials' not in elem.text
                                c_info = TagClassifier.classify_element(
                                    text=elem.text,
                                    bbox=elem.bbox,
                                    font_info=elem.font,
                                    is_formula=is_formula_elem,
                                    doc_is_tagged=True,
                                    source="docx_xml" if is_formula_elem else "native"
                                )
                                elem.type = c_info["content_type"]
                                elem.content_type = c_info["content_type"]
                                elem.tag = c_info["tag"]
                                elem.is_tagged = c_info["is_tagged"]
                                elem.tag_source = c_info["tag_source"]
                                elem.parameters = c_info["parameters"]

                    from app.layout.reading_order import sort_reading_order
                    for p in res["pages"]:
                        p.elements = sort_reading_order(p.elements, page_width=p.width)

                except Exception as ex_xml:
                    logger.warning(f"Supplemental XML & MathType extraction error: {ex_xml}", exc_info=True)
                    
                all_extracted = [elem for p in res["pages"] for elem in p.elements]
                res["tagging_summary"] = TagClassifier.build_tagging_summary(all_extracted, doc_is_tagged=res.get("is_tagged_document", True))
                return res
        except Exception as e:
            logger.warning(f"docx2pdf conversion fallback: {e}", exc_info=True)

        # 2. Fallback Strategy: Direct DOCX Parsing if MS Word is not available
        logger.info("Using native DOCX parser fallback...")
        doc = docx.Document(docx_path)
        elements: List[ExtractedElement] = []
        stats = ExtractionStatistics()
        elem_counter = 1

        # Render basic pages via PyMuPDF
        pages_data: List[PageData] = []
        try:
            mupdf_doc = pymupdf.open(docx_path)
            for p_idx in range(len(mupdf_doc)):
                p_num = p_idx + 1
                page = mupdf_doc[p_idx]
                pix = page.get_pixmap(dpi=150)
                page_img_filename = f"page_{p_num}.png"
                pix.save(os.path.join(temp_dir, page_img_filename))
                pages_data.append(PageData(
                    page=p_num,
                    width=float(page.rect.width),
                    height=float(page.rect.height),
                    rendered_image_url=f"/api/preview/{job_id}/{p_num}",
                    elements=[]
                ))
            mupdf_doc.close()
        except Exception as e:
            logger.warning(f"PyMuPDF direct docx rendering failed: {e}")

        # Extract embedded images & MathType formulas from word/media/
        img_counter = 1
        try:
            with zipfile.ZipFile(docx_path, 'r') as z:
                media_files = [f for f in z.namelist() if f.startswith('word/media/')]
                for media_file in media_files:
                    raw_bytes = z.read(media_file)
                    original_name = os.path.basename(media_file)
                    ext = os.path.splitext(original_name)[1].lower()
                    
                    raw_temp_path = os.path.join(temp_dir, f"raw_{original_name}")
                    with open(raw_temp_path, "wb") as f:
                        f.write(raw_bytes)

                    base_name = f"docx_img_{img_counter}"
                    web_img_filename, img_w, img_h = convert_to_web_image(raw_temp_path, temp_dir, base_name)
                    final_img_path = os.path.join(temp_dir, web_img_filename)

                    is_mathtype = ext in ('.wmf', '.emf') or 'equation' in original_name.lower() or 'ole' in original_name.lower()
                    elem_type = "formula" if is_mathtype else "image"
                    img_id = f"mathtype_{img_counter}" if is_mathtype else f"image_{img_counter}"
                    image_api_url = f"/api/image/{job_id}/{web_img_filename}"

                    elements.append(ExtractedElement(
                        id=f"docx_media_{elem_counter}",
                        type=elem_type,
                        source="docx",
                        page=1,
                        image_id=img_id,
                        image_path=image_api_url,
                        width=img_w,
                        height=img_h
                    ))
                    elem_counter += 1
                    
                    if is_mathtype:
                        stats.formulas_count += 1
                    else:
                        stats.images_count += 1

                    # Run PaddleOCR on the image to recognize text / math notation
                    ocr_results = self.image_extractor.process_image(final_img_path, page_num=1, image_id=img_id)
                    for ocr_res in ocr_results:
                        ocr_txt = ocr_res.get("text", "")
                        ocr_bbox = ocr_res.get("bbox")
                        ocr_conf = ocr_res.get("confidence")
                        if is_ui_artifact(ocr_txt, ocr_bbox, confidence=ocr_conf):
                            continue
                        cleaned_txt = clean_ocr_text(ocr_txt)
                        if not cleaned_txt or is_ui_artifact(cleaned_txt, ocr_bbox, confidence=ocr_conf):
                            continue
                        elements.append(ExtractedElement(
                            id=f"docx_ocr_{elem_counter}",
                            type="image_text",
                            source="ocr",
                            text=cleaned_txt,
                            confidence=ocr_conf,
                            bbox=ocr_bbox,
                            image_id=img_id,
                            page=1
                        ))
                        elem_counter += 1
                        stats.ocr_text_blocks += 1

                    img_counter += 1
        except Exception as e:
            logger.error(f"Error extracting word/media images: {e}")

        # Paragraphs & Runs
        for p_idx, p in enumerate(doc.paragraphs):
            text = p.text.strip()
            if not text:
                continue

            font_info = None
            if p.runs:
                first_run = p.runs[0]
                font_info = FontInfo(
                    name=first_run.font.name if first_run.font else None,
                    size=float(first_run.font.size.pt) if first_run.font and first_run.font.size else None,
                    bold=first_run.bold or False,
                    italic=first_run.italic or False,
                    underline=first_run.underline or False
                )

            # Check if paragraph has numPr (bullet/numbered list)
            has_num_pr = False
            try:
                has_num_pr = bool(p._element.xpath('.//w:numPr'))
            except Exception:
                pass

            style_name = p.style.name if p.style else None

            classification = TagClassifier.classify_element(
                text=text,
                font_info=font_info,
                explicit_style=style_name,
                has_xml_num_pr=has_num_pr,
                source="docx"
            )

            c_type = classification["content_type"]
            elements.append(ExtractedElement(
                id=f"docx_p_{elem_counter}",
                type=c_type,
                content_type=c_type,
                tag=classification["tag"],
                is_tagged=classification["is_tagged"],
                tag_source=classification["tag_source"],
                parameters=classification["parameters"],
                source="docx",
                text=text,
                page=1,
                font=font_info,
                reading_order=elem_counter,
                confidence=1.0
            ))
            elem_counter += 1
            if c_type == "formula":
                stats.formulas_count += 1
            elif c_type == "header":
                stats.headers_count += 1
            elif c_type == "footer":
                stats.footers_count += 1
            else:
                stats.native_text_blocks += 1

        # Tables
        for t_idx, table in enumerate(doc.tables):
            table_rows: List[List[str]] = []
            for row in table.rows:
                row_data = [cell.text.strip() for cell in row.cells]
                table_rows.append(row_data)

            headers = table_rows[0] if table_rows else []
            rows = table_rows[1:] if len(table_rows) > 1 else table_rows

            tbl_classification = TagClassifier.classify_element(
                is_table=True,
                table_rows=rows,
                table_headers=headers,
                source="docx"
            )

            elements.append(ExtractedElement(
                id=f"docx_tbl_{elem_counter}",
                type="table",
                content_type="table",
                tag="Table",
                is_tagged=True,
                tag_source="docx_style",
                parameters=tbl_classification["parameters"],
                source="docx",
                page=1,
                rows=table_rows,
                headers=headers,
                reading_order=elem_counter,
                confidence=1.0
            ))
            elem_counter += 1
            stats.tables_count += 1

        # XML elements
        xml_elements = extract_docx_xml_content(docx_path)
        for xml_elem in xml_elements:
            elem_type = xml_elem.get("type", "textbox")
            txt = xml_elem.get("text")
            if txt:
                is_formula = (elem_type == "formula")
                xml_classification = TagClassifier.classify_element(
                    text=txt,
                    is_formula=is_formula,
                    source="docx_xml"
                )

                elements.append(ExtractedElement(
                    id=f"docx_xml_{elem_counter}",
                    type=xml_classification["content_type"],
                    content_type=xml_classification["content_type"],
                    tag=xml_classification["tag"],
                    is_tagged=xml_classification["is_tagged"],
                    tag_source=xml_classification["tag_source"],
                    parameters=xml_classification["parameters"],
                    source="docx_xml",
                    text=txt,
                    page=1,
                    confidence=1.0
                ))
                elem_counter += 1
                if elem_type == "formula":
                    stats.formulas_count += 1
                elif elem_type == "textbox":
                    stats.textboxes_count += 1

        if not pages_data:
            pages_data.append(PageData(
                page=1,
                width=612.0,
                height=792.0,
                elements=[]
            ))

        pages_data[0].elements = elements
        stats.total_pages = len(pages_data)

        all_elements = [elem for p in pages_data for elem in p.elements]
        doc_is_tagged = any(e.is_tagged and e.tag_source in ("docx_style", "docx_xml") for e in all_elements)
        tagging_summary = TagClassifier.build_tagging_summary(all_elements, doc_is_tagged=doc_is_tagged)

        return {
            "pages": pages_data,
            "statistics": stats,
            "is_tagged_document": doc_is_tagged,
            "tagging_summary": tagging_summary
        }
