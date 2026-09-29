from typing import List
from app.models.extraction_models import ExtractedElement

def sort_reading_order(elements: List[ExtractedElement], page_width: float = 612.0) -> List[ExtractedElement]:
    """
    Sorts extracted elements on a single page into logical reading order.
    Detects multi-column vs single-column flow and sorts top-to-bottom, left-to-right.
    Assigns sequential `reading_order` numbers to each element.
    """
    if not elements:
        return elements

    # Separate elements with bboxes and without bboxes
    valid_elements = [e for e in elements if e.bbox and len(e.bbox) == 4]
    no_bbox_elements = [e for e in elements if not e.bbox or len(e.bbox) < 4]

    # Check for multi-column layout by inspecting x0 distribution
    midpoint = page_width / 2.0
    left_col = []
    right_col = []
    full_width = []

    for elem in valid_elements:
        x0, y0, x1, y1 = elem.bbox
        width = x1 - x0
        if width > page_width * 0.65:
            full_width.append(elem)
        elif (x0 + x1) / 2.0 < midpoint:
            left_col.append(elem)
        else:
            right_col.append(elem)

    is_multi_column = len(left_col) > 3 and len(right_col) > 3

    def sort_key_single_col(elem: ExtractedElement):
        # Line grouping: bucket y0 by ~10px tolerance
        y0 = elem.bbox[1]
        x0 = elem.bbox[0]
        y_bucket = round(y0 / 12.0) * 12.0
        return (y_bucket, x0)

    if is_multi_column:
        # Sort left column top-to-bottom, then right column top-to-bottom
        left_sorted = sorted(left_col, key=sort_key_single_col)
        right_sorted = sorted(right_col, key=sort_key_single_col)
        full_sorted = sorted(full_width, key=sort_key_single_col)
        
        # Interleave full width elements based on vertical position
        combined = []
        all_cols = sorted(full_sorted + left_sorted + right_sorted, key=lambda e: (e.bbox[1], e.bbox[0]))
        sorted_valid = all_cols
    else:
        sorted_valid = sorted(valid_elements, key=sort_key_single_col)

    final_sorted = sorted_valid + no_bbox_elements

    for idx, elem in enumerate(final_sorted):
        elem.reading_order = idx + 1

    return final_sorted
