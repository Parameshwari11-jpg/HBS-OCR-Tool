import pymupdf
from app.originality.pdf_checker import PDFOriginalityChecker

checker = PDFOriginalityChecker()
doc = pymupdf.open('backend/uploads/f96caa41-6027-4f43-b1a7-41ff82226c3c.pdf')

# Let's inspect page 7 (0-indexed 6) and page 8 (0-indexed 7)
for p_idx in [6, 7]:
    p_num = p_idx + 1
    page = doc[p_idx]
    orig_lines = checker._extract_page_text_lines(page, p_num=p_num)
    print(f"\n=== PAGE {p_num} (Total orig lines: {len(orig_lines)}) ===")
    for idx, l in enumerate(orig_lines):
        if any(w in l for w in ['Management', 'Delete', 'Contains tasks', 'Flag']):
            print(f"  orig[{idx}]: {repr(l)}")
