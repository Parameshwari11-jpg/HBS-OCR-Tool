from typing import List, Dict, Any
from app.models.extraction_models import ExtractedElement
from app.utils.bbox import calculate_relationship, bbox_intersection, bbox_area

def detect_overlaps(elements: List[ExtractedElement]) -> List[ExtractedElement]:
    """
    Detects spatial overlaps and relationships between all extracted elements on a page.
    Classifies overlapping scenarios (text inside image, text over image, text under image, etc.)
    without deleting any element.
    """
    if not elements or len(elements) < 2:
        return elements

    for i in range(len(elements)):
        elem_a = elements[i]
        if not elem_a.bbox or len(elem_a.bbox) < 4:
            continue
            
        for j in range(i + 1, len(elements)):
            elem_b = elements[j]
            if not elem_b.bbox or len(elem_b.bbox) < 4:
                continue
                
            rel = calculate_relationship(elem_a.bbox, elem_b.bbox)
            if rel["relationship"] != "none" and rel["overlap_ratio_a"] > 0.1:
                # Add relationship links
                if elem_b.id not in elem_a.overlapping_element_ids:
                    elem_a.overlapping_element_ids.append(elem_b.id)
                if elem_a.id not in elem_b.overlapping_element_ids:
                    elem_b.overlapping_element_ids.append(elem_a.id)

                # Classify specific case:
                # Case B: OCR text inside image
                if elem_a.type == "image" and elem_b.type == "image_text":
                    elem_b.overlap_relationship = "text_inside_image"
                elif elem_b.type == "image" and elem_a.type == "image_text":
                    elem_a.overlap_relationship = "text_inside_image"
                    
                # Case C / D: Native text overlapping with Image
                elif elem_a.type == "text" and elem_b.type == "image":
                    elem_a.overlap_relationship = "text_overlapping_image"
                elif elem_b.type == "text" and elem_a.type == "image":
                    elem_b.overlap_relationship = "text_overlapping_image"
                else:
                    elem_a.overlap_relationship = rel["relationship"]
                    elem_b.overlap_relationship = rel["relationship"]

    return elements
