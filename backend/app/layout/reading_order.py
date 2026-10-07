import re
from typing import List, Optional, Tuple, Dict, Any
from app.models.extraction_models import ExtractedElement

def _sort_line_clusters(elements: List[ExtractedElement]) -> List[ExtractedElement]:
    """
    Sorts a group of elements row-by-row (top-to-bottom, left-to-right within lines).
    Clusters elements into visual reading lines based on vertical overlap/center alignment.
    """
    if not elements:
        return []
    if len(elements) == 1:
        return list(elements)

    # Sort primarily by y0, then x0
    sorted_elements = sorted(elements, key=lambda e: (e.bbox[1] if e.bbox else 0, e.bbox[0] if e.bbox else 0))
    lines: List[List[ExtractedElement]] = []

    for elem in sorted_elements:
        if not elem.bbox or len(elem.bbox) < 4:
            continue
        e_yc = (elem.bbox[1] + elem.bbox[3]) / 2.0
        e_h = max(1.0, elem.bbox[3] - elem.bbox[1])
        placed = False
        for line in lines:
            ref_yc = sum((e.bbox[1] + e.bbox[3]) / 2.0 for e in line) / len(line)
            ref_h = sum((e.bbox[3] - e.bbox[1]) for e in line) / len(line)
            # Two elements share the same line if their vertical centers are close
            if abs(e_yc - ref_yc) <= max(4.0, 0.45 * min(e_h, ref_h)):
                line.append(elem)
                placed = True
                break
        if not placed:
            lines.append([elem])

    # Sort lines by average vertical center
    lines.sort(key=lambda line: sum((e.bbox[1] + e.bbox[3]) / 2.0 for e in line) / len(line))

    # Sort each line strictly left-to-right
    sorted_res: List[ExtractedElement] = []
    for line in lines:
        line.sort(key=lambda e: e.bbox[0] if e.bbox else 0)
        sorted_res.extend(line)

    return sorted_res

def _detect_columns(elements: List[ExtractedElement], page_width: float = 612.0) -> List[List[ExtractedElement]]:
    """
    Detects visual vertical columns based on horizontal intervals and bounding box projections.
    Returns a list of columns, where each column is an ordered list of elements (top-to-bottom).
    If no multi-column structure exists, returns a single column.
    """
    if len(elements) < 3:
        return [_sort_line_clusters(elements)]

    # Compute bounding boxes
    boxes = [e.bbox for e in elements if e.bbox and len(e.bbox) == 4]
    if not boxes:
        return [_sort_line_clusters(elements)]

    min_x = min(b[0] for b in boxes)
    max_x = max(b[2] for b in boxes)
    span_w = max_x - min_x

    # If the text spans less than 120pt wide, it's essentially single-column
    if span_w < 120.0:
        return [_sort_line_clusters(elements)]

    # Project vertical column occupancy across horizontal x-axis
    # Discretize span into 2pt buckets
    step = 2.0
    num_buckets = max(1, int(span_w / step) + 1)
    occupancy = [0] * num_buckets

    for b in boxes:
        # Give a small margin
        start_idx = max(0, int((b[0] - min_x) / step))
        end_idx = min(num_buckets - 1, int((b[2] - min_x) / step))
        for idx in range(start_idx, end_idx + 1):
            occupancy[idx] += 1

    # Find gutter gaps: consecutive zero or near-zero buckets
    # A true column gutter should have zero occupancy across a width of at least 10pt (5 buckets)
    min_gutter_buckets = int(10.0 / step)
    gutters: List[Tuple[float, float]] = []

    in_gutter = False
    g_start = 0
    for idx, count in enumerate(occupancy):
        if count == 0 and not in_gutter:
            in_gutter = True
            g_start = idx
        elif count > 0 and in_gutter:
            in_gutter = False
            g_len = idx - g_start
            if g_len >= min_gutter_buckets:
                gx0 = min_x + g_start * step
                gx1 = min_x + idx * step
                gutters.append((gx0, gx1))

    if in_gutter:
        g_len = num_buckets - g_start
        if g_len >= min_gutter_buckets:
            gx0 = min_x + g_start * step
            gx1 = min_x + num_buckets * step
            gutters.append((gx0, gx1))

    # Filter out margin gutters at extreme ends
    valid_gutters = [
        (g0, g1) for (g0, g1) in gutters
        if (g0 - min_x) >= 30.0 and (max_x - g1) >= 30.0
    ]

    if not valid_gutters:
        return [_sort_line_clusters(elements)]

    # Partition elements into columns based on gutter boundaries
    # Column boundaries: [min_x, mid_gutter1, mid_gutter2, ..., max_x + 10]
    split_points = [(g0 + g1) / 2.0 for g0, g1 in valid_gutters]
    
    num_cols = len(split_points) + 1
    cols: List[List[ExtractedElement]] = [[] for _ in range(num_cols)]

    for elem in elements:
        b = elem.bbox
        e_xc = (b[0] + b[2]) / 2.0
        # Assign to column
        assigned_col = 0
        for sp in split_points:
            if e_xc > sp:
                assigned_col += 1
            else:
                break
        cols[assigned_col].append(elem)

    # Validate that columns have a balanced distribution (each col has at least 1 element)
    non_empty_cols = [c for c in cols if len(c) > 0]
    if len(non_empty_cols) <= 1:
        return [_sort_line_clusters(elements)]

    # Sort each column top-to-bottom
    sorted_cols = [_sort_line_clusters(c) for c in non_empty_cols]
    return sorted_cols

def _is_form_region(elements: List[ExtractedElement]) -> bool:
    """
    Determines if a cluster of elements behaves as a form (labels followed by inputs/blanks).
    Forms exhibit prompt/value pairs on the same line or form field conventions.
    """
    if len(elements) < 2:
        return False

    form_prompt_patterns = [
        r':\s*$', r'\bname\b', r'\bemail\b', r'\bphone\b', r'\baddress\b',
        r'\bdate\b', r'\bsignature\b', r'\bfirst\s*name\b', r'\blast\s*name\b',
        r'\bcity\b', r'\bstate\b', r'\bzip\b', r'\[\s*input\s*\]', r'\[\s*x?\s*\]',
        r'[_]{3,}' # blank fill-in lines
    ]

    matches = 0
    colon_ends = 0
    total = len(elements)

    for elem in elements:
        t = (elem.text or "").strip().lower()
        if not t:
            continue
        if t.endswith(":"):
            colon_ends += 1
        if any(re.search(pat, t) for pat in form_prompt_patterns):
            matches += 1

    # If significant proportion of elements end with colons or match form prompt patterns
    if colon_ends >= 2 or (matches >= 2 and matches / max(1, total) >= 0.25):
        return True

    return False

def _is_toc_region(elements: List[ExtractedElement]) -> bool:
    """
    Determines if a region represents a Table of Contents (TOC).
    TOC entries typically feature dot leaders, section/unit/chapter numbers, or trailing page numbers.
    """
    if len(elements) < 3:
        return False

    toc_indicators = 0
    for elem in elements:
        t = (elem.text or "").strip()
        # Dot leaders e.g. "Chapter 1 .......... 15" or ". . . . 20"
        if re.search(r'\.{3,}', t) or re.search(r'(\.\s*){3,}', t):
            toc_indicators += 1
        # Title ending in standalone page number e.g. "Introduction  5"
        elif re.search(r'[A-Za-z\s]+[\s\t]{2,}\d+$', t):
            toc_indicators += 1
        # Explicit TOC tag or keywords
        elif getattr(elem, "tag", "") == "TOC" or getattr(elem, "type", "") == "toc":
            toc_indicators += 1

    return (toc_indicators >= 2) or (toc_indicators / len(elements) >= 0.3)

def _is_table_region(elements: List[ExtractedElement]) -> bool:
    """
    Checks if elements belong to a standard data table.
    """
    for elem in elements:
        if getattr(elem, "type", "") == "table" or getattr(elem, "tag", "") == "Table":
            return True
        if getattr(elem, "rows", None) or getattr(elem, "headers", None):
            return True
    return False

def _is_columnar_list(elements: List[ExtractedElement]) -> bool:
    """
    Checks if elements represent a list arranged in visual columns (e.g. lists of names, cities, vocab).
    """
    if len(elements) < 4:
        return False
    bullet_or_short = 0
    for elem in elements:
        t = (elem.text or "").strip()
        # Short phrases (1-4 words) or bullet items
        if 0 < len(t.split()) <= 4 or re.match(r'^([•\-\*\d+\.]|\([a-z0-9]+\))\s+', t):
            bullet_or_short += 1
    return (bullet_or_short / len(elements)) >= 0.65

def _partition_mixed_page(elements: List[ExtractedElement], page_width: float = 612.0) -> List[List[ExtractedElement]]:
    """
    Partitions a page into logical vertical and structural regions (Mixed-Layout Pages).
    Identifies spanning headers/titles, multi-column body blocks, tables, and footers.
    """
    if len(elements) <= 3:
        return [elements]

    # Separate elements with bboxes
    valid = [e for e in elements if e.bbox and len(e.bbox) == 4]
    if len(valid) <= 3:
        return [elements]

    # Sort vertically
    valid.sort(key=lambda e: (e.bbox[1], e.bbox[0]))

    # Detect spanning elements (elements that span more than 65% of the page text width)
    min_x = min(b.bbox[0] for b in valid)
    max_x = max(b.bbox[2] for b in valid)
    total_w = max_x - min_x

    # Identify distinct tables or explicit table elements
    table_elems = [e for e in valid if _is_table_region([e])]
    table_ids = set(id(e) for e in table_elems)

    regions: List[List[ExtractedElement]] = []
    current_region: List[ExtractedElement] = []

    for elem in valid:
        # If this is a table element, isolate as its own region
        if id(elem) in table_ids:
            if current_region:
                regions.append(current_region)
                current_region = []
            regions.append([elem])
            continue

        b = elem.bbox
        w = b[2] - b[0]
        is_spanner = (total_w > 150.0 and w / total_w >= 0.70)
        
        # Check vertical gap to previous element in current region
        if current_region:
            prev_b = current_region[-1].bbox
            vert_gap = b[1] - prev_b[3]
            # Significant vertical gap (> 30pt) suggests a new logical section/block
            if vert_gap > 35.0:
                regions.append(current_region)
                current_region = []

        # If it's a wide spanner (title/header/footer), separate into its own region
        if is_spanner and len(current_region) > 0:
            regions.append(current_region)
            current_region = [elem]
            regions.append(current_region)
            current_region = []
        elif is_spanner:
            regions.append([elem])
        else:
            current_region.append(elem)

    if current_region:
        regions.append(current_region)

    return regions

def sort_reading_order(elements: List[ExtractedElement], page_width: float = 612.0) -> List[ExtractedElement]:
    """
    Comprehensive Layout-Aware Reading-Order System.
    Determines the natural and accessible reading order based on document structure:
    1. Single-column content: Top -> Bottom
    2. Multi-column content: Column 1 (Top -> Bottom) -> Column 2 (Top -> Bottom) ...
    3. Multi-column Table of Contents (TOC): Column-wise (Column 1 -> Column 2 ...)
    4. Forms: Row-wise (Field 1 -> Input 1 -> Field 2 -> Input 2)
    5. Standard Tables: Row-wise (Row 1 -> Row 2 -> Row 3)
    6. Columnar Lists: Column-wise (Column 1 -> Column 2)
    7. Mixed-Layout Pages: Vertical section-by-section breakdown applying appropriate ordering.
    """
    if not elements:
        return elements

    # Separate elements with bboxes and text vs non-text or no bboxes
    valid_elements = [
        e for e in elements
        if e.bbox and len(e.bbox) == 4
    ]
    text_elements = [e for e in valid_elements if e.text and e.text.strip()]
    other_elements = [e for e in valid_elements if not (e.text and e.text.strip())]
    no_bbox_elements = [e for e in elements if not e.bbox or len(e.bbox) < 4]

    if not text_elements:
        for idx, elem in enumerate(elements):
            elem.reading_order = idx + 1
        return elements

    # Partition page into logical structural regions
    regions = _partition_mixed_page(text_elements, page_width=page_width)
    ordered_valid: List[ExtractedElement] = []

    for region in regions:
        if not region:
            continue

        # Rule 5: Standard Data Tables -> Row-wise order
        if _is_table_region(region):
            ordered_valid.extend(_sort_line_clusters(region))
            continue

        # Rule 4: Forms -> Row-wise order
        if _is_form_region(region):
            ordered_valid.extend(_sort_line_clusters(region))
            continue

        # Rule 3: Table of Contents (TOC) -> Column-wise order if multi-column
        if _is_toc_region(region):
            columns = _detect_columns(region, page_width=page_width)
            for col in columns:
                ordered_valid.extend(col)
            continue

        # Rule 6: Columnar Lists -> Column-wise order
        if _is_columnar_list(region):
            columns = _detect_columns(region, page_width=page_width)
            for col in columns:
                ordered_valid.extend(col)
            continue

        # Rule 2: Normal Multi-Column Content -> Column 1 (Top -> Bottom), then Column 2 (Top -> Bottom) ...
        # Rule 1: Normal Single-Column Content -> single column output from _detect_columns
        columns = _detect_columns(region, page_width=page_width)
        for col in columns:
            ordered_valid.extend(col)

    # Recombine with non-text and no-bbox elements
    final_sorted = ordered_valid + other_elements + no_bbox_elements

    # Assign sequential reading_order indices
    for idx, elem in enumerate(final_sorted):
        elem.reading_order = idx + 1

    return final_sorted
