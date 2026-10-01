from typing import List
from app.models.extraction_models import ExtractedElement

def sort_reading_order(elements: List[ExtractedElement], page_width: float = 612.0) -> List[ExtractedElement]:
    """
    Sorts extracted elements on a single page into logical reading order.
    Clusters elements into visual reading lines, sorting lines top-to-bottom
    and elements within each line left-to-right.
    Assigns sequential `reading_order` numbers to each element.
    """
    if not elements:
        return elements

    # Separate elements with bboxes and without bboxes
    valid_elements = [e for e in elements if e.bbox and len(e.bbox) == 4]
    no_bbox_elements = [e for e in elements if not e.bbox or len(e.bbox) < 4]

    if not valid_elements:
        for idx, elem in enumerate(elements):
            elem.reading_order = idx + 1
        return elements

    # Sort primarily by y0, then x0
    sorted_elements = sorted(valid_elements, key=lambda e: (e.bbox[1], e.bbox[0]))
    lines: List[List[ExtractedElement]] = []

    for elem in sorted_elements:
        e_yc = (elem.bbox[1] + elem.bbox[3]) / 2.0
        e_h = max(1.0, elem.bbox[3] - elem.bbox[1])
        placed = False
        for line in lines:
            ref_yc = sum((e.bbox[1] + e.bbox[3]) / 2.0 for e in line) / len(line)
            ref_h = sum((e.bbox[3] - e.bbox[1]) for e in line) / len(line)
            # Two elements are on the same line if their vertical centers are close
            if abs(e_yc - ref_yc) <= max(4.0, 0.4 * min(e_h, ref_h)):
                line.append(elem)
                placed = True
                break
        if not placed:
            lines.append([elem])

    # Sort lines by average vertical center
    lines.sort(key=lambda line: sum((e.bbox[1] + e.bbox[3]) / 2.0 for e in line) / len(line))

    # Sort each line strictly left-to-right
    sorted_valid: List[ExtractedElement] = []
    for line in lines:
        line.sort(key=lambda e: e.bbox[0])
        sorted_valid.extend(line)

    final_sorted = sorted_valid + no_bbox_elements

    for idx, elem in enumerate(final_sorted):
        elem.reading_order = idx + 1

    return final_sorted

