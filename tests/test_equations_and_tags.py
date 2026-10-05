import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))
from app.extractors.mtef_decoder import format_fraction, MTEFDecoder
from app.layout.tag_classifier import TagClassifier


class TestEquationsAndTags(unittest.TestCase):
    def test_format_fraction_math_fidelity(self):
        """Verify that compound fractions correctly enclose numerators/denominators, while single terms stay clean."""
        res1 = format_fraction("p + r", "q")
        self.assertEqual(res1, "(p + r)/q")

        res2 = format_fraction("p - r", "q")
        self.assertEqual(res2, "(p - r)/q")

        res3 = format_fraction("3a", "a - 4")
        self.assertEqual(res3, "3a/(a - 4)")

        res4 = format_fraction("c^2", "c - 6")
        self.assertEqual(res4, "c^2/(c - 6)")

        res5 = format_fraction("7", "10")
        self.assertEqual(res5, "7/10")

    def test_tag_classifier_math_vs_prose(self):
        """Verify that prose text with inline symbols is classified as paragraph, and formulas as formula."""
        prose = "Let p, q, and r represent polynomials where q ≠ 0. Then,"
        cls_prose = TagClassifier.classify_element(text=prose, source="docx_style")
        self.assertEqual(cls_prose["content_type"], "paragraph")
        self.assertEqual(cls_prose["tag"], "P")

        eq = "1. p/q + r/q = (p + r)/q      2. p/q - r/q = (p - r)/q"
        cls_eq = TagClassifier.classify_element(text=eq, source="docx_xml")
        self.assertEqual(cls_eq["content_type"], "formula")
        self.assertEqual(cls_eq["tag"], "Formula")
        self.assertTrue(cls_eq["is_tagged"])
        self.assertEqual(cls_eq["parameters"]["formula_type"], "latex_or_ascii")

        note = "Note: To add or subtract rational expressions with the same denominator:"
        cls_note = TagClassifier.classify_element(text=note, source="docx_style")
        self.assertEqual(cls_note["content_type"], "paragraph")
        self.assertEqual(cls_note["tag"], "P")


if __name__ == '__main__':
    unittest.main()
