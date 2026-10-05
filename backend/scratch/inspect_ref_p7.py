import pymupdf
from app.originality.pdf_checker import PDFOriginalityChecker

checker = PDFOriginalityChecker()
doc = pymupdf.open('backend/uploads/f96caa41-6027-4f43-b1a7-41ff82226c3c.pdf')
page = doc[6] # page 7
ref_text, ver_type, conf = checker._extract_page_reference_text(page, page_num=7)
lines = [l.strip() for l in ref_text.split('\n') if l.strip()]
print(f"Total lines: {len(lines)}")
for idx, l in enumerate(lines):
    if any(k in l for k in ['Management', 'Contains tasks', 'rename', 'Button Name']):
        print(f"  line {idx}: {repr(l)}")
