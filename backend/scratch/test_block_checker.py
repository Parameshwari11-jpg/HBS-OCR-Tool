import pymupdf
import json
from app.originality.normalizer import TextNormalizer
from app.originality.diff_engine import DiffEngine

doc = pymupdf.open('backend/uploads/f96caa41-6027-4f43-b1a7-41ff82226c3c.pdf')
with open('backend/temp/f96caa41-6027-4f43-b1a7-41ff82226c3c/result.json', 'r', encoding='utf-8') as f:
    res_data = json.load(f)

for p_idx in [6, 7]: # Pages 7 and 8
    p_num = p_idx + 1
    page = doc[p_idx]
    
    # 1. Native text extraction preserving block integrity
    text_dict = page.get_text("dict")
    blocks = text_dict.get("blocks", [])
    
    valid_blocks = []
    for b in blocks:
        if b.get("type") == 0:
            # Watermark check
            b_raw = " ".join("".join(s.get("text", "") for s in l.get("spans", [])) for l in b.get("lines", [])).lower()
            if any(frag in b_raw for frag in ["exclusive use", "excl e use", "do not print", "do n print", "academic partnership", "evaluation only"]):
                continue
            
            # Extract lines of this block
            lines = []
            for l in b.get("lines", []):
                span_parts = []
                for span in l.get("spans", []):
                    st = span.get("text", "")
                    if st:
                        if span_parts and not span_parts[-1].endswith(" ") and not st.startswith(" ") and not (st and st[0] in ".,;:!?)]}%"):
                            span_parts.append(" ")
                        span_parts.append(st)
                line_str = "".join(span_parts).strip()
                if line_str:
                    lines.append(line_str)
            if lines:
                bbox = b.get("bbox", (0, 0, 0, 0))
                valid_blocks.append((bbox[1], bbox[3], bbox[0], bbox[2], lines))

    # Sort blocks: group by visual line (yc), then x0
    grouped = []
    for y0, y1, x0, x1, lines in sorted(valid_blocks, key=lambda b: (b[0], b[2])):
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

    grouped.sort(key=lambda g: sum((item[0] + item[1]) / 2.0 for item in g) / len(g))

    orig_lines = []
    for g in grouped:
        g.sort(key=lambda item: item[2])
        for y0, y1, x0, x1, lines in g:
            for l in lines:
                orig_lines.append(TextNormalizer.normalize_line(l))

    # Extracted lines from result.json
    p_data = [p for p in res_data['pages'] if p['page'] == p_num][0]
    ext_lines = []
    for e in sorted(p_data['elements'], key=lambda x: x.get('reading_order') or 999):
        if not e.get('possible_duplicate') and e.get('text'):
            for l in e['text'].split('\n'):
                if l.strip():
                    ext_lines.append(TextNormalizer.normalize_line(l.strip()))

    diffs, mismatches = DiffEngine.compare_page_lines(orig_lines, ext_lines, page_num=p_num)
    print(f"\n=== PAGE {p_num} (Mismatches: {len(mismatches)}) ===")
    for m in mismatches:
        print(f"  {m.diff_type} | orig: {repr(m.orig_text[:40])} -> ext: {repr(m.extracted_text[:40])}")
