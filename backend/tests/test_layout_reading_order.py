import sys
import unittest
from pathlib import Path

# Add backend directory to path
backend_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_path))

from app.models.extraction_models import ExtractedElement
from app.layout.reading_order import sort_reading_order

class TestLayoutAwareReadingOrder(unittest.TestCase):
    """
    Test suite for the layout-aware reading-order system covering:
    - Test 1: Single-column content (Top -> Bottom)
    - Test 2: Two-column content (Column 1 -> Column 2)
    - Test 3: Three-column content (Column 1 -> Column 2 -> Column 3)
    - Test 4: Standard table (Row 1 -> Row 2 -> Row 3)
    - Test 5: Form (Field 1 -> Input 1 -> Field 2 -> Input 2)
    - Test 6: Multi-column Table of Contents (TOC) (Column 1 -> Column 2)
    - Test 7: Mixed-layout page (Title -> Multi-column -> Table -> Footer)
    - Test 8: OCR/scanned document layout preservation
    """

    def test_1_single_column_top_to_bottom(self):
        """Single-column content must follow strict top-to-bottom reading order."""
        elems = [
            ExtractedElement(id="e1", page=1, type="text", source="native", text="Paragraph 1", bbox=[50.0, 50.0, 550.0, 80.0]),
            ExtractedElement(id="e2", page=1, type="text", source="native", text="Paragraph 2", bbox=[50.0, 100.0, 550.0, 130.0]),
            ExtractedElement(id="e3", page=1, type="text", source="native", text="Paragraph 3", bbox=[50.0, 150.0, 550.0, 180.0]),
        ]
        ordered = sort_reading_order(elems, page_width=612.0)
        ordered_texts = [e.text for e in ordered]
        self.assertEqual(ordered_texts, ["Paragraph 1", "Paragraph 2", "Paragraph 3"])
        self.assertEqual([e.reading_order for e in ordered], [1, 2, 3])

    def test_2_two_column_reading_order(self):
        """
        Two-column content:
        Column 1: Text A, Text B, Text C
        Column 2: Text D, Text E, Text F
        Must read: A -> B -> C -> D -> E -> F, not A -> D -> B -> E...
        """
        elems = [
            # Column 1 items (x from 50 to 250)
            ExtractedElement(id="e1", page=1, type="text", source="native", text="Text A", bbox=[50.0, 100.0, 250.0, 120.0]),
            ExtractedElement(id="e2", page=1, type="text", source="native", text="Text B", bbox=[50.0, 130.0, 250.0, 150.0]),
            ExtractedElement(id="e3", page=1, type="text", source="native", text="Text C", bbox=[50.0, 160.0, 250.0, 180.0]),
            # Column 2 items (x from 350 to 550, with clear gutter 250-350)
            ExtractedElement(id="e4", page=1, type="text", source="native", text="Text D", bbox=[350.0, 100.0, 550.0, 120.0]),
            ExtractedElement(id="e5", page=1, type="text", source="native", text="Text E", bbox=[350.0, 130.0, 550.0, 150.0]),
            ExtractedElement(id="e6", page=1, type="text", source="native", text="Text F", bbox=[350.0, 160.0, 550.0, 180.0]),
        ]
        ordered = sort_reading_order(elems, page_width=612.0)
        ordered_texts = [e.text for e in ordered]
        self.assertEqual(ordered_texts, ["Text A", "Text B", "Text C", "Text D", "Text E", "Text F"])

    def test_3_three_column_reading_order(self):
        """Three-column content: Col 1 -> Col 2 -> Col 3."""
        elems = [
            # Col 1 (50 - 180)
            ExtractedElement(id="c1_1", page=1, type="text", source="native", text="Col1 Item 1", bbox=[50.0, 100.0, 180.0, 120.0]),
            ExtractedElement(id="c1_2", page=1, type="text", source="native", text="Col1 Item 2", bbox=[50.0, 130.0, 180.0, 150.0]),
            # Col 2 (230 - 360)
            ExtractedElement(id="c2_1", page=1, type="text", source="native", text="Col2 Item 1", bbox=[230.0, 100.0, 360.0, 120.0]),
            ExtractedElement(id="c2_2", page=1, type="text", source="native", text="Col2 Item 2", bbox=[230.0, 130.0, 360.0, 150.0]),
            # Col 3 (410 - 540)
            ExtractedElement(id="c3_1", page=1, type="text", source="native", text="Col3 Item 1", bbox=[410.0, 100.0, 540.0, 120.0]),
            ExtractedElement(id="c3_2", page=1, type="text", source="native", text="Col3 Item 2", bbox=[410.0, 130.0, 540.0, 150.0]),
        ]
        ordered = sort_reading_order(elems, page_width=612.0)
        ordered_texts = [e.text for e in ordered]
        expected = ["Col1 Item 1", "Col1 Item 2", "Col2 Item 1", "Col2 Item 2", "Col3 Item 1", "Col3 Item 2"]
        self.assertEqual(ordered_texts, expected)

    def test_4_standard_table_row_wise(self):
        """
        Standard data table must be read row-wise:
        Header 1 -> Header 2 -> Row1 Cell 1 -> Row1 Cell 2 ...
        """
        elems = [
            ExtractedElement(id="th1", page=1, type="table", source="native", text="Name", bbox=[50.0, 100.0, 150.0, 120.0]),
            ExtractedElement(id="th2", page=1, type="table", source="native", text="Age", bbox=[200.0, 100.0, 280.0, 120.0]),
            ExtractedElement(id="th3", page=1, type="table", source="native", text="City", bbox=[350.0, 100.0, 450.0, 120.0]),
            ExtractedElement(id="td1_1", page=1, type="table", source="native", text="Arun", bbox=[50.0, 130.0, 150.0, 150.0]),
            ExtractedElement(id="td1_2", page=1, type="table", source="native", text="25", bbox=[200.0, 130.0, 280.0, 150.0]),
            ExtractedElement(id="td1_3", page=1, type="table", source="native", text="Chennai", bbox=[350.0, 130.0, 450.0, 150.0]),
            ExtractedElement(id="td2_1", page=1, type="table", source="native", text="Priya", bbox=[50.0, 160.0, 150.0, 180.0]),
            ExtractedElement(id="td2_2", page=1, type="table", source="native", text="23", bbox=[200.0, 160.0, 280.0, 180.0]),
            ExtractedElement(id="td2_3", page=1, type="table", source="native", text="Coimbatore", bbox=[350.0, 160.0, 450.0, 180.0]),
        ]
        ordered = sort_reading_order(elems, page_width=612.0)
        ordered_texts = [e.text for e in ordered]
        expected = [
            "Name", "Age", "City",
            "Arun", "25", "Chennai",
            "Priya", "23", "Coimbatore"
        ]
        self.assertEqual(ordered_texts, expected)

    def test_5_form_row_wise(self):
        """
        Form content: Field 1 -> Input 1 -> Field 2 -> Input 2 ...
        Must NOT be read as Column 1 (all labels) then Column 2 (all inputs).
        """
        elems = [
            ExtractedElement(id="f1_lbl", page=1, type="text", source="native", text="Name:", bbox=[50.0, 100.0, 150.0, 120.0]),
            ExtractedElement(id="f1_inp", page=1, type="text", source="native", text="John Doe", bbox=[200.0, 100.0, 350.0, 120.0]),
            ExtractedElement(id="f2_lbl", page=1, type="text", source="native", text="Email:", bbox=[50.0, 130.0, 150.0, 150.0]),
            ExtractedElement(id="f2_inp", page=1, type="text", source="native", text="john@example.com", bbox=[200.0, 130.0, 350.0, 150.0]),
            ExtractedElement(id="f3_lbl", page=1, type="text", source="native", text="Phone:", bbox=[50.0, 160.0, 150.0, 180.0]),
            ExtractedElement(id="f3_inp", page=1, type="text", source="native", text="555-0199", bbox=[200.0, 160.0, 350.0, 180.0]),
        ]
        ordered = sort_reading_order(elems, page_width=612.0)
        ordered_texts = [e.text for e in ordered]
        expected = ["Name:", "John Doe", "Email:", "john@example.com", "Phone:", "555-0199"]
        self.assertEqual(ordered_texts, expected)

    def test_6_multi_column_toc(self):
        """Multi-column Table of Contents: Column 1 -> Column 2."""
        elems = [
            # Col 1 TOC entries
            ExtractedElement(id="t1", page=1, type="text", source="native", text="1. Getting Started ............ 1", bbox=[50.0, 100.0, 260.0, 120.0]),
            ExtractedElement(id="t2", page=1, type="text", source="native", text="2. Basics of Grammar .......... 15", bbox=[50.0, 130.0, 260.0, 150.0]),
            ExtractedElement(id="t3", page=1, type="text", source="native", text="3. Vocabulary Practice ........ 30", bbox=[50.0, 160.0, 260.0, 180.0]),
            # Col 2 TOC entries
            ExtractedElement(id="t4", page=1, type="text", source="native", text="4. Advanced Topics ............ 45", bbox=[340.0, 100.0, 550.0, 120.0]),
            ExtractedElement(id="t5", page=1, type="text", source="native", text="5. Culture and Reading ........ 60", bbox=[340.0, 130.0, 550.0, 150.0]),
            ExtractedElement(id="t6", page=1, type="text", source="native", text="6. Index and Appendix ......... 75", bbox=[340.0, 160.0, 550.0, 180.0]),
        ]
        ordered = sort_reading_order(elems, page_width=612.0)
        ordered_texts = [e.text for e in ordered]
        expected = [
            "1. Getting Started ............ 1",
            "2. Basics of Grammar .......... 15",
            "3. Vocabulary Practice ........ 30",
            "4. Advanced Topics ............ 45",
            "5. Culture and Reading ........ 60",
            "6. Index and Appendix ......... 75"
        ]
        self.assertEqual(ordered_texts, expected)

    def test_7_mixed_layout_page(self):
        """
        Mixed page layout:
        Spanning Title -> 2-Column Article -> Table -> Footer
        Each region must follow its respective reading order.
        """
        elems = [
            # Title spanner
            ExtractedElement(id="title", page=1, type="heading_1", source="native", text="Annual Scientific Report", bbox=[50.0, 40.0, 550.0, 70.0]),
            # 2-column article
            ExtractedElement(id="col1_p1", page=1, type="text", source="native", text="Col1 Para1", bbox=[50.0, 120.0, 250.0, 150.0]),
            ExtractedElement(id="col1_p2", page=1, type="text", source="native", text="Col1 Para2", bbox=[50.0, 160.0, 250.0, 190.0]),
            ExtractedElement(id="col2_p1", page=1, type="text", source="native", text="Col2 Para1", bbox=[350.0, 120.0, 550.0, 150.0]),
            ExtractedElement(id="col2_p2", page=1, type="text", source="native", text="Col2 Para2", bbox=[350.0, 160.0, 550.0, 190.0]),
            # Table (isolated below article with vert_gap > 35)
            ExtractedElement(id="th_1", page=1, type="table", source="native", text="Metric", bbox=[50.0, 240.0, 200.0, 260.0]),
            ExtractedElement(id="th_2", page=1, type="table", source="native", text="Score", bbox=[300.0, 240.0, 450.0, 260.0]),
            ExtractedElement(id="td_1", page=1, type="table", source="native", text="Accuracy", bbox=[50.0, 270.0, 200.0, 290.0]),
            ExtractedElement(id="td_2", page=1, type="table", source="native", text="99.5%", bbox=[300.0, 270.0, 450.0, 290.0]),
            # Footer spanner
            ExtractedElement(id="footer", page=1, type="footer", source="native", text="Page 1 of 12 - Confidential", bbox=[50.0, 750.0, 550.0, 770.0]),
        ]
        ordered = sort_reading_order(elems, page_width=612.0)
        ordered_texts = [e.text for e in ordered]
        expected = [
            "Annual Scientific Report",
            "Col1 Para1", "Col1 Para2",
            "Col2 Para1", "Col2 Para2",
            "Metric", "Score",
            "Accuracy", "99.5%",
            "Page 1 of 12 - Confidential"
        ]
        self.assertEqual(ordered_texts, expected)

    def test_8_ocr_scanned_layout_preservation(self):
        """Scanned/OCR fragments with source='ocr' correctly partition into columns."""
        elems = [
            ExtractedElement(id="ocr_c1_1", page=1, type="text", source="ocr", text="OCR Column 1 Line 1", bbox=[45.0, 100.0, 240.0, 118.0]),
            ExtractedElement(id="ocr_c1_2", page=1, type="text", source="ocr", text="OCR Column 1 Line 2", bbox=[46.0, 125.0, 242.0, 143.0]),
            ExtractedElement(id="ocr_c2_1", page=1, type="text", source="ocr", text="OCR Column 2 Line 1", bbox=[320.0, 102.0, 515.0, 120.0]),
            ExtractedElement(id="ocr_c2_2", page=1, type="text", source="ocr", text="OCR Column 2 Line 2", bbox=[321.0, 126.0, 516.0, 144.0]),
        ]
        ordered = sort_reading_order(elems, page_width=612.0)
        ordered_texts = [e.text for e in ordered]
        expected = [
            "OCR Column 1 Line 1",
            "OCR Column 1 Line 2",
            "OCR Column 2 Line 1",
            "OCR Column 2 Line 2"
        ]
        self.assertEqual(ordered_texts, expected)

if __name__ == "__main__":
    unittest.main()
