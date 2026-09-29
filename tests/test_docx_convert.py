import os
import threading
import pythoncom
import pymupdf
from docx2pdf import convert

def run_conversion():
    pythoncom.CoInitialize()
    try:
        convert("tests/test_img.docx", "tests/thread_test.pdf")
        print("Conversion in thread succeeded!")
    finally:
        pythoncom.CoUninitialize()

t = threading.Thread(target=run_conversion)
t.start()
t.join()

if os.path.exists("tests/thread_test.pdf"):
    doc = pymupdf.open("tests/thread_test.pdf")
    print("Rendered PDF pages:", len(doc))
    p = doc[0]
    pix = p.get_pixmap(dpi=150)
    pix.save("tests/exact_original_sample.png")
    print("Saved exact_original_sample.png:", pix.width, pix.height)
