from typing import List
from app.models.extraction_models import ExtractedElement
from app.utils.normalization import calculate_text_similarity, normalize_text
from app.utils.bbox import bbox_iou

def detect_duplicates(elements: List[ExtractedElement]) -> List[ExtractedElement]:
    """
    Compares native text, OCR text, and PP-Structure text elements to flag possible duplicates.
    Does NOT remove elements, but marks `possible_duplicate = True` and links `related_native_text_id`.
    Requires spatial overlap or near-identical text to avoid falsely deleting distinct UI elements.
    """
    if not elements or len(elements) < 2:
        return elements

    native_elements = [e for e in elements if e.source in ("native", "docx") and e.text]
    ocr_elements = [e for e in elements if e.source in ("ocr", "pp_structure") and e.text]

    for ocr_elem in ocr_elements:
        norm_ocr_text = normalize_text(ocr_elem.text)
        if len(norm_ocr_text) < 2:
            continue

        best_sim = 0.0
        best_native_id = None
        has_overlap = False

        for native_elem in native_elements:
            norm_native_text = normalize_text(native_elem.text)
            if len(norm_native_text) < 2:
                continue

            sim = calculate_text_similarity(norm_ocr_text, norm_native_text)
            
            # Spatial check: do bounding boxes overlap?
            iou = 0.0
            if ocr_elem.bbox and native_elem.bbox:
                iou = bbox_iou(ocr_elem.bbox, native_elem.bbox)

            if iou > 0.15:
                has_overlap = True
                sim = max(sim, 0.70 + (iou * 0.30))

            if sim > best_sim:
                best_sim = sim
                best_native_id = native_elem.id

        # If spatial overlap exists, threshold is 0.70
        # If NO spatial overlap exists (elements are in different places), require near-identical text (>= 0.90) and length > 15
        if best_native_id:
            if has_overlap and best_sim >= 0.70:
                ocr_elem.possible_duplicate = True
                ocr_elem.related_native_text_id = best_native_id
            elif not has_overlap and best_sim >= 0.90 and len(norm_ocr_text) > 15:
                ocr_elem.possible_duplicate = True
                ocr_elem.related_native_text_id = best_native_id

    return elements
