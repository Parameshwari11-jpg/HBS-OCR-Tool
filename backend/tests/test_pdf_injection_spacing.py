import sys
import unittest
import pymupdf
from pathlib import Path

# Add backend directory to path
backend_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_path))

from app.utils.spacing_engine import SpacingEngine, should_insert_space
from app.layout.reading_order import sort_reading_order
from app.models.extraction_models import ExtractedElement

class TestPdfInjectionSpacing(unittest.TestCase):
    """
    Automated tests validating generic PDF text-layer injection spacing.
    Verifies that generated PDF text layers retain proper whitespace for Adobe Acrobat
    selection/tagging across word boundaries, line breaks, punctuation, units, etc.
    """

    def setUp(self):
        self.engine = SpacingEngine.get_instance()

    def _simulate_page_injection(self, elements):
        """
        Simulates the exact PDF text layer injection logic used in export_injected_pdf
        and returns the resulting text and raw PDF content streams.
        """
        doc = pymupdf.open()
        page = doc.new_page(width=612.0, height=792.0)
        helv_font = pymupdf.Font("helv")

        sorted_elems = sort_reading_order(elements, page_width=612.0)
        num_elems = len(sorted_elems)
        items_to_inject = []

        for i, elem in enumerate(sorted_elems):
            txt = (elem.text or "").strip()
            bbox = elem.bbox or [50.0, 50.0, 300.0, 70.0]
            x0, y0, x1, y1 = bbox
            box_w = max(1.0, float(x1 - x0))
            box_h = max(8.0, float(y1 - y0))
            fs = box_h * 0.92
            y_baseline = y1 - (box_h * 0.08)
            pt = pymupdf.Point(x0, y_baseline)

            if i < num_elems - 1:
                next_elem = sorted_elems[i + 1]
                next_txt = (next_elem.text or "").strip()
                next_bbox = next_elem.bbox or [50.0, 50.0, 300.0, 70.0]

                e1_yc = (y0 + y1) / 2.0
                e2_yc = (next_bbox[1] + next_bbox[3]) / 2.0
                same_line = abs(e1_yc - e2_yc) <= max(4.0, 0.45 * min(box_h, float(next_bbox[3] - next_bbox[1])))

                if same_line and next_bbox[0] >= x1:
                    coord_gap = float(next_bbox[0] - x1)
                else:
                    coord_gap = None

                if self.engine.should_insert_space(txt, next_txt, coord_gap=coord_gap, font_size=fs):
                    txt = txt + " "
            else:
                last_c = txt[-1] if txt else ""
                if last_c and last_c not in "-–—'’([{‘“«$#@":
                    txt = txt + " "

            tw = helv_font.text_length(txt, fontsize=fs)
            sx = box_w / max(0.1, tw)
            morph = (pt, pymupdf.Matrix(sx, 1.0))
            items_to_inject.append((pt, txt, fs, morph))

        for pt, txt, fs, morph in items_to_inject:
            page.insert_text(pt, txt, fontsize=fs, render_mode=3, morph=morph)

        page.clean_contents()

        extracted_text = page.get_text()
        raw_streams = [doc.xref_stream(s).decode("latin1", errors="ignore") for s in page.get_contents()]
        doc.close()
        return extracted_text, raw_streams

    def test_two_normal_words_separate_fragments(self):
        """Normal words across separate fragments must receive space and not concatenate."""
        elems = [
            ExtractedElement(id="e1", page=1, type="text", source="ocr", text="Contributing", bbox=[50.0, 100.0, 150.0, 120.0]),
            ExtractedElement(id="e2", page=1, type="text", source="ocr", text="Writers", bbox=[160.0, 100.0, 240.0, 120.0]),
        ]
        text, streams = self._simulate_page_injection(elems)
        self.assertNotIn("ContributingWriters", text)
        self.assertIn("Contributing ", text)
        self.assertIn("Writers", text)
        # Check raw PDF operand contains trailing space inside TJ/Tj string
        self.assertTrue(any("Contributing " in s or "<436f6e747269627574696e6720>" in s for s in streams))

    def test_multi_word_phrase_separate_fragments(self):
        """Multi-word phrases split into separate fragments e.g. 'Field Test' + 'Participants'."""
        elems = [
            ExtractedElement(id="e1", page=1, type="text", source="ocr", text="Field Test", bbox=[100.0, 50.0, 200.0, 75.0]),
            ExtractedElement(id="e2", page=1, type="text", source="ocr", text="Participants", bbox=[100.0, 80.0, 220.0, 105.0]),
        ]
        text, _ = self._simulate_page_injection(elems)
        self.assertNotIn("Field TestParticipants", text)
        self.assertIn("Field Test ", text)
        self.assertIn("Participants", text)

    def test_sentence_split_across_lines(self):
        """Sentence split across lines e.g. 'grammar' at end of line, 'presentations' at start of next."""
        elems = [
            ExtractedElement(id="e1", page=1, type="text", source="ocr", text="Ms. Harwood wrote the grammar", bbox=[50.0, 100.0, 250.0, 120.0]),
            ExtractedElement(id="e2", page=1, type="text", source="ocr", text="presentations, created activities for", bbox=[50.0, 125.0, 280.0, 145.0]),
        ]
        text, _ = self._simulate_page_injection(elems)
        self.assertNotIn("grammarpresentations", text)
        self.assertIn("Ms. Harwood wrote the grammar ", text)
        self.assertIn("presentations, created activities for", text)

    def test_punctuation_attachment_preservation(self):
        """Punctuation marks must remain attached without inserted space."""
        elems = [
            ExtractedElement(id="e1", page=1, type="text", source="ocr", text="word", bbox=[50.0, 100.0, 80.0, 115.0]),
            ExtractedElement(id="e2", page=1, type="text", source="ocr", text=",", bbox=[81.0, 100.0, 88.0, 115.0]),
            ExtractedElement(id="e3", page=1, type="text", source="ocr", text="next", bbox=[95.0, 100.0, 130.0, 115.0]),
        ]
        text, _ = self._simulate_page_injection(elems)
        self.assertIn("word,", text)
        self.assertNotIn("word ,", text)

    def test_apostrophes_and_contractions(self):
        """Contractions e.g. 'don' + \"'t\" must remain attached."""
        elems = [
            ExtractedElement(id="e1", page=1, type="text", source="ocr", text="don", bbox=[50.0, 100.0, 75.0, 115.0]),
            ExtractedElement(id="e2", page=1, type="text", source="ocr", text="'t", bbox=[75.5, 100.0, 88.0, 115.0]),
        ]
        text, _ = self._simulate_page_injection(elems)
        self.assertIn("don't", text)
        self.assertNotIn("don 't", text)

    def test_hyphenated_words(self):
        """Hyphenated words e.g. 'state-' + 'of-the-art' must remain attached."""
        elems = [
            ExtractedElement(id="e1", page=1, type="text", source="ocr", text="state-", bbox=[50.0, 100.0, 90.0, 115.0]),
            ExtractedElement(id="e2", page=1, type="text", source="ocr", text="of-the-art", bbox=[92.0, 100.0, 160.0, 115.0]),
        ]
        text, _ = self._simulate_page_injection(elems)
        self.assertIn("state-of-the-art", text)
        self.assertNotIn("state- of-the-art", text)

    def test_numbers_and_units(self):
        """Numbers and units e.g. '100' + 'px', '5' + 'kg' remain attached."""
        elems = [
            ExtractedElement(id="e1", page=1, type="text", source="ocr", text="100", bbox=[50.0, 100.0, 75.0, 115.0]),
            ExtractedElement(id="e2", page=1, type="text", source="ocr", text="px", bbox=[76.0, 100.0, 95.0, 115.0]),
        ]
        text, _ = self._simulate_page_injection(elems)
        self.assertIn("100px", text)
        self.assertNotIn("100 px", text)

    def test_decimals_and_numbers(self):
        """Decimals e.g. '3.' + '14' must remain attached."""
        elems = [
            ExtractedElement(id="e1", page=1, type="text", source="ocr", text="3.", bbox=[50.0, 100.0, 65.0, 115.0]),
            ExtractedElement(id="e2", page=1, type="text", source="ocr", text="14", bbox=[66.0, 100.0, 82.0, 115.0]),
        ]
        text, _ = self._simulate_page_injection(elems)
        self.assertIn("3.14", text)
        self.assertNotIn("3. 14", text)

    def test_opening_brackets(self):
        """Opening brackets e.g. '(' + 'example)' must not have space after bracket."""
        elems = [
            ExtractedElement(id="e1", page=1, type="text", source="ocr", text="(", bbox=[50.0, 100.0, 58.0, 115.0]),
            ExtractedElement(id="e2", page=1, type="text", source="ocr", text="example)", bbox=[59.0, 100.0, 110.0, 115.0]),
        ]
        text, _ = self._simulate_page_injection(elems)
        self.assertIn("(example)", text)
        self.assertNotIn("( example)", text)

if __name__ == "__main__":
    unittest.main()
