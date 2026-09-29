import os
import sys
import unittest

sys.path.insert(0, os.path.abspath("backend"))

import pymupdf as fitz
from app.extractors.pdf_extractor import PDFExtractor
from app.layout.overlap_detector import detect_overlaps
from app.layout.duplicate_detector import detect_duplicates
from app.models.extraction_models import ExtractedElement

class TestPDFExtractor(unittest.TestCase):
    def setUp(self):
        self.test_pdf = "tests/sample_test.pdf"
        os.makedirs("tests", exist_ok=True)
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), "Hello World PDF Text", fontsize=12)
        doc.save(self.test_pdf)
        doc.close()

    def tearDown(self):
        if os.path.exists(self.test_pdf):
            os.remove(self.test_pdf)

    def test_overlap_detector(self):
        elem_native = ExtractedElement(
            id="text_1", type="text", source="native", text="Sample", bbox=[10, 10, 100, 100]
        )
        elem_image = ExtractedElement(
            id="img_1", type="image", source="native", bbox=[10, 10, 100, 100]
        )
        elements = detect_overlaps([elem_native, elem_image])
        self.assertIn("img_1", elem_native.overlapping_element_ids)

    def test_duplicate_detector(self):
        elem_native = ExtractedElement(
            id="text_1", type="text", source="native", text="Temperature: 25°C", bbox=[10, 10, 100, 50]
        )
        elem_ocr = ExtractedElement(
            id="ocr_1", type="image_text", source="ocr", text="Temperature: 25°C", bbox=[10, 10, 100, 50]
        )
        elements = detect_duplicates([elem_native, elem_ocr])
        self.assertTrue(elem_ocr.possible_duplicate)
        self.assertEqual(elem_ocr.related_native_text_id, "text_1")

if __name__ == "__main__":
    unittest.main()
