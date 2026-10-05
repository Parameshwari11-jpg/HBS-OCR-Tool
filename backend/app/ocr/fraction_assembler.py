import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger("fraction_assembler")

def is_math_fraction_term(s: str) -> bool:
    """
    Validates whether a string is a legitimate mathematical fraction term (numerator or denominator).
    Rejects normal sentences, UI labels, colons, words, and dialog text so that lines are never
    artificially merged into single lines with slashes.
    """
    s = s.strip()
    if not s or len(s) > 18:
        return False
    # Reject sentence punctuation, colons, semicolons, currency, quotes
    if any(c in s for c in [':', ';', ',', '!', '?', '"', "'", '@', '#', '$', '%', '&']):
        return False
    math_words = {'sin', 'cos', 'tan', 'cot', 'sec', 'csc', 'log', 'ln', 'lim', 'exp', 'mod', 'sqrt'}
    words = s.split()
    if len(words) > 4:
        return False
    for w in words:
        w_clean = re.sub(r'[^a-zA-Z]', '', w).lower()
        # Common English words with 3 or more characters are not fraction terms
        if len(w_clean) >= 3 and w_clean not in math_words:
            return False
    # Pure integers in fractions are small (e.g. 1/2, 3/4, 7/10). Multi-digit values > 99 are row counts / data
    if s.isdigit() and int(s) > 99:
        return False
    # Must contain at least one digit or single-letter variable or math operator
    if not re.search(r'[0-9a-zA-Z\+\-\*]', s):
        return False
    return True

def is_part_of_table_column(item_idx: int, items: List[Dict[str, Any]]) -> bool:
    """Returns True if the item is part of a column of 3 or more vertically stacked items."""
    b = items[item_idx].get('bbox', [0, 0, 0, 0])
    cx = (b[0] + b[2]) / 2.0
    w = max(1.0, b[2] - b[0])
    
    col_count = 0
    for other in items:
        ob = other.get('bbox', [0, 0, 0, 0])
        ocx = (ob[0] + ob[2]) / 2.0
        ow = max(1.0, ob[2] - ob[0])
        h_overlap = max(0.0, min(b[2], ob[2]) - max(b[0], ob[0]))
        if abs(cx - ocx) <= max(12.0, 0.4 * max(w, ow)) or h_overlap > 0.4 * min(w, ow):
            col_count += 1
            if col_count >= 3:
                return True
    return False

def assemble_vertical_fractions(ocr_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Pairs vertically aligned OCR elements (numerator and denominator separated by
    a fraction line or vertical gap) into clean fractional math formulas: `num/den`.
    Only applies to legitimate mathematical terms, preserving sentences and labels
    on their original separate lines.
    """
    if not ocr_results or len(ocr_results) < 2:
        return ocr_results

    sorted_items = sorted(
        ocr_results,
        key=lambda x: (x.get('bbox', [0, 0, 0, 0])[1], x.get('bbox', [0, 0, 0, 0])[0])
    )
    used = set()
    assembled = []

    for i, top in enumerate(sorted_items):
        if i in used:
            continue
        top_txt = top.get('text', '').strip()
        if not is_math_fraction_term(top_txt) or is_part_of_table_column(i, sorted_items):
            assembled.append(top)
            used.add(i)
            continue

        tb = top.get('bbox', [0, 0, 0, 0])
        tw = max(1.0, tb[2] - tb[0])
        th = max(1.0, tb[3] - tb[1])
        tcx = (tb[0] + tb[2]) / 2.0

        pair_idx = None
        for j in range(i + 1, len(sorted_items)):
            if j in used:
                continue
            bot_txt = sorted_items[j].get('text', '').strip()
            if not is_math_fraction_term(bot_txt) or is_part_of_table_column(j, sorted_items):
                continue

            bb = sorted_items[j].get('bbox', [0, 0, 0, 0])
            bw = max(1.0, bb[2] - bb[0])
            bh = max(1.0, bb[3] - bb[1])
            bcx = (bb[0] + bb[2]) / 2.0

            v_gap = bb[1] - tb[3]
            h_overlap = max(0.0, min(tb[2], bb[2]) - max(tb[0], bb[0]))
            min_w = min(tw, bw)

            # Check if j is vertically below i within reasonable fraction gap
            # and horizontally aligned with overlapping bounds or close centers
            if -5 <= v_gap < max(th, bh) * 3.5:
                if abs(tcx - bcx) < max(tw, bw) * 0.7 or h_overlap > 0.25 * min_w:
                    pair_idx = j
                    break

        if pair_idx is not None:
            bot = sorted_items[pair_idx]
            bb = bot.get('bbox', [0, 0, 0, 0])
            bot_txt = bot.get('text', '').strip()

            # Format cleanly as num/den with parentheses for composite expressions
            bot_clean = re.sub(r'([a-zA-Z0-9])\s*([+\-])\s*([a-zA-Z0-9])', r'\1 \2 \3', bot_txt)
            top_clean = re.sub(r'([a-zA-Z0-9])\s*([+\-])\s*([a-zA-Z0-9])', r'\1 \2 \3', top_txt)
            def _needs_parens_asm(s: str) -> bool:
                s = s.strip()
                if s.startswith('(') and s.endswith(')'):
                    return False
                return bool(re.search(r'[\+\-\=]', s))

            top_str = f"({top_clean})" if _needs_parens_asm(top_clean) else top_clean
            bot_str = f"({bot_clean})" if _needs_parens_asm(bot_clean) else bot_clean
            frac_txt = f"{top_str}/{bot_str}"

            merged_bbox = [
                min(tb[0], bb[0]),
                tb[1],
                max(tb[2], bb[2]),
                bb[3]
            ]
            merged_conf = min(top.get('confidence', 95.0), bot.get('confidence', 95.0))
            assembled.append({
                'id': top.get('id', f'frac_{i}'),
                'page': top.get('page', 1),
                'type': 'formula',
                'is_formula': True,
                'source': 'ocr',
                'text': frac_txt,
                'confidence': merged_conf,
                'bbox': merged_bbox
            })
            used.add(i)
            used.add(pair_idx)
        else:
            assembled.append(top)
            used.add(i)

    return assembled
