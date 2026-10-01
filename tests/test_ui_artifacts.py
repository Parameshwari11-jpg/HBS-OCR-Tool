import os
import sys
import unittest

sys.path.insert(0, os.path.abspath("backend"))
from app.utils.normalization import is_ui_artifact, clean_ocr_text, clean_leading_ocr_checkbox

class TestUIArtifactsAndCleaning(unittest.TestCase):
    def test_window_caption_controls(self):
        # Window minimize/close buttons should be detected as UI artifacts
        self.assertTrue(is_ui_artifact('_ x', [10, 10, 30, 25], confidence=95.0))
        self.assertTrue(is_ui_artifact('_x', [10, 10, 30, 25], confidence=95.0))
        self.assertTrue(is_ui_artifact('_ X', [10, 10, 30, 25], confidence=95.0))
        self.assertTrue(is_ui_artifact('- x', [10, 10, 30, 25], confidence=95.0))
        self.assertTrue(is_ui_artifact('— x', [10, 10, 30, 25], confidence=95.0))
        self.assertTrue(is_ui_artifact('X', [484, 7, 498, 21], confidence=71.0))
        self.assertTrue(is_ui_artifact('x', [10, 10, 25, 25], confidence=80.0))

    def test_dropdown_arrow_buttons(self):
        # Dropdown arrows in comboboxes
        self.assertTrue(is_ui_artifact('V', [326, 124, 336, 134], confidence=91.8))
        self.assertTrue(is_ui_artifact('v', [10, 10, 25, 25], confidence=89.0))
        self.assertTrue(is_ui_artifact('v.', [10, 10, 25, 25], confidence=90.0))
        self.assertTrue(is_ui_artifact('▼', [10, 10, 25, 25], confidence=90.0))

        # Drop-up / scrollbar up-arrow buttons ('A', 'a') in small UI control buttons
        self.assertTrue(is_ui_artifact('A', [469, 114, 478, 124], confidence=98.81)) # Page 2 exact detection (9x10px)
        self.assertTrue(is_ui_artifact('A', [470, 75, 478, 85], confidence=87.51))   # Page 2 exact detection (8x10px)
        self.assertTrue(is_ui_artifact('a', [10, 10, 20, 20], confidence=90.0))


    def test_standalone_checkbox_glyphs_and_ticks(self):
        # Standalone checkbox boxes and ticks
        self.assertTrue(is_ui_artifact('0', [10, 10, 25, 25], confidence=80.0))
        self.assertTrue(is_ui_artifact('1', [10, 10, 25, 25], confidence=75.0))
        self.assertTrue(is_ui_artifact('☐', [10, 10, 25, 25], confidence=90.0))
        self.assertTrue(is_ui_artifact('☑', [10, 10, 25, 25], confidence=90.0))
        self.assertTrue(is_ui_artifact('✓', [10, 10, 25, 25], confidence=90.0))

    def test_clean_leading_ocr_checkbox(self):
        # Checkboxes misrecognized as numbers/letters directly preceding words
        self.assertEqual(clean_ocr_text('0Show shading'), 'Show shading')
        self.assertEqual(clean_ocr_text('1CHECK'), 'CHECK')
        self.assertEqual(clean_ocr_text('0Break on this field'), 'Break on this field')
        self.assertEqual(clean_ocr_text('1PAY_DAYS'), 'PAY_DAYS')
        self.assertEqual(clean_ocr_text('0 Show shading'), 'Show shading')
        self.assertEqual(clean_ocr_text('0 Count records in break'), 'Count records in break')
        self.assertEqual(clean_ocr_text('SShow shading'), 'Show shading')
        self.assertEqual(clean_ocr_text('vCHECK'), 'CHECK')
        self.assertEqual(clean_ocr_text('xAMOUNT'), 'AMOUNT')
        self.assertEqual(clean_ocr_text('[ ] Show break line'), 'Show break line')

    def test_preserves_legitimate_document_content(self):
        # Numbered lists must NOT be stripped
        s1 = '8. Create grand totals for the AMOUNT field and set the font to bold. Click Next.'
        self.assertEqual(clean_ocr_text(s1), s1)
        self.assertFalse(is_ui_artifact(s1, [10, 10, 400, 25], confidence=99.0))

        s2 = '1. Once the report has been created'
        self.assertEqual(clean_ocr_text(s2), s2)

        s3 = '5.3 Print Preview and Print the Report'
        self.assertEqual(clean_ocr_text(s3), s3)

        # Pure numbers (e.g., table cells, counts) must be preserved
        self.assertEqual(clean_ocr_text('220'), '220')
        self.assertFalse(is_ui_artifact('220', [10, 10, 40, 25], confidence=99.0))
        self.assertEqual(clean_ocr_text('280'), '280')
        self.assertEqual(clean_ocr_text('180'), '180')
        self.assertEqual(clean_ocr_text('1/4/2019'), '1/4/2019')

        # Real text labels
        self.assertEqual(clean_ocr_text('Count of records'), 'Count of records')
        self.assertFalse(is_ui_artifact('Count of records', [10, 10, 120, 25], confidence=98.0))
        self.assertEqual(clean_ocr_text('CaseWare IDEA'), 'CaseWare IDEA')
        self.assertFalse(is_ui_artifact('CaseWare IDEA', [10, 10, 100, 25], confidence=99.0))
        self.assertEqual(clean_ocr_text('Accounts Payable'), 'Accounts Payable')
        self.assertEqual(clean_ocr_text('AMOUNT'), 'AMOUNT')
        self.assertEqual(clean_ocr_text('Next >'), 'Next >')
        self.assertEqual(clean_ocr_text('< Back'), '< Back')
        self.assertEqual(clean_ocr_text('Finish'), 'Finish')
        self.assertEqual(clean_ocr_text('Cancel'), 'Cancel')
        self.assertEqual(clean_ocr_text('Help'), 'Help')

        # Ordinals and technical acronyms
        self.assertEqual(clean_ocr_text('1st place'), '1st place')
        self.assertEqual(clean_ocr_text('2nd row'), '2nd row')
        self.assertEqual(clean_ocr_text('3D model'), '3D model')
        self.assertEqual(clean_ocr_text('4K resolution'), '4K resolution')

if __name__ == '__main__':
    unittest.main()
