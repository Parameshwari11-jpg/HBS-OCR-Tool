import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from app.originality.normalizer import TextNormalizer
from app.originality.diff_engine import DiffEngine
from app.originality.accuracy import AccuracyCalculator
from app.originality.models import DifferenceType, SeverityLevel, StatusType
from app.originality.comparator import originality_comparator
from app.originality.report_generator import ReportGenerator


class TestOriginalityVerification(unittest.TestCase):
    def test_text_normalizer(self):
        """Verify normalization of whitespace, smart quotes, dashes, and line endings."""
        raw = "Line 1 with   spaces  and  “smart quotes”\r\nLine 2 with em—dash and \u00a0non-breaking space."
        norm = TextNormalizer.normalize_text(raw)
        self.assertIn('"smart quotes"', norm)
        self.assertIn('-', norm)
        self.assertNotIn('\r', norm)
        self.assertNotIn('  ', norm)

        numbers = TextNormalizer.extract_numbers("Price is $500.50, up 25% by 2026.")
        self.assertIn("500.50", numbers)
        self.assertIn("25%", numbers)
        self.assertIn("2026", numbers)

    def test_exact_match_100_percent(self):
        """Verify that identical original and extracted text produces 100% accuracy and PASS."""
        lines = [
            "Artificial Intelligence is transforming modern healthcare.",
            "Documents are processed securely and accurately."
        ]
        line_diffs, mismatches = DiffEngine.compare_page_lines(lines, lines, page_num=1)
        self.assertEqual(len(mismatches), 0)
        self.assertTrue(all(ld.tag == 'equal' for ld in line_diffs))

        words = TextNormalizer.extract_words("\n".join(lines))
        acc, status = AccuracyCalculator.calculate_page_accuracy(words, words, mismatches)
        self.assertEqual(acc, 100.0)
        self.assertEqual(status, StatusType.PASS)

    def test_number_mismatch_detection(self):
        """Verify that number changes (500 -> 50) are flagged as high severity NUMBER_MISMATCH."""
        orig = ["The system processes 500 documents per day."]
        ext = ["The system processes 50 documents per day."]
        line_diffs, mismatches = DiffEngine.compare_page_lines(orig, ext, page_num=4)

        num_mms = [m for m in mismatches if m.diff_type == DifferenceType.NUMBER_MISMATCH]
        self.assertTrue(len(num_mms) > 0)
        self.assertEqual(num_mms[0].severity, SeverityLevel.HIGH)
        self.assertIn("500", num_mms[0].difference)
        self.assertIn("50", num_mms[0].difference)

        words_orig = TextNormalizer.extract_words(orig[0])
        words_ext = TextNormalizer.extract_words(ext[0])
        acc, status = AccuracyCalculator.calculate_page_accuracy(words_orig, words_ext, mismatches)
        # Because of number error, status must NOT be PASS
        self.assertNotEqual(status, StatusType.PASS)

    def test_same_word_count_different_numbers(self):
        """Verify Section 24 rule: equal word count does NOT produce 100% when content differs."""
        orig = ["The employee has 25 days leave."]
        ext = ["The employee has 35 days leave."]
        self.assertEqual(len(orig[0].split()), len(ext[0].split()))

        line_diffs, mismatches = DiffEngine.compare_page_lines(orig, ext, page_num=1)
        self.assertTrue(any(m.diff_type == DifferenceType.NUMBER_MISMATCH for m in mismatches))

        words_orig = TextNormalizer.extract_words(orig[0])
        words_ext = TextNormalizer.extract_words(ext[0])
        acc, status = AccuracyCalculator.calculate_page_accuracy(words_orig, words_ext, mismatches)
        self.assertLess(acc, 100.0)
        self.assertNotEqual(status, StatusType.PASS)

    def test_character_level_ocr_error_detection(self):
        """Verify character-level diff detecting OCR letter dropouts (Accessibility -> Accessibilty)."""
        orig = ["Accessibility features must be tested."]
        ext = ["Accessibilty features must be tested."]
        line_diffs, mismatches = DiffEngine.compare_page_lines(orig, ext, page_num=1)

        char_mms = [m for m in mismatches if m.char_diffs]
        self.assertTrue(len(char_mms) > 0)
        char_diff = char_mms[0].char_diffs[0]
        self.assertEqual(char_diff.diff_type, "missing_char")
        self.assertEqual(char_diff.char, "i")

    def test_missing_and_extra_text(self):
        """Verify detection of omitted lines and unprompted extra lines."""
        orig = ["Line 1", "Line 2 to be deleted", "Line 3"]
        ext = ["Line 1", "Line 3", "Extra Line 4"]

        line_diffs, mismatches = DiffEngine.compare_page_lines(orig, ext, page_num=1)
        missing = [m for m in mismatches if m.diff_type == DifferenceType.MISSING_TEXT]
        extra = [m for m in mismatches if m.diff_type == DifferenceType.EXTRA_TEXT]

        self.assertTrue(len(missing) > 0)
        self.assertTrue(len(extra) > 0)

    def test_report_generation_formats(self):
        """Verify export generation for JSON, CSV, and PDF."""
        orig = ["Line 1", "The system processes 500 documents per day."]
        ext = ["Line 1", "The system processes 50 documents per day."]
        line_diffs, mismatches = DiffEngine.compare_page_lines(orig, ext, page_num=1)
        acc, status = AccuracyCalculator.calculate_page_accuracy(
            TextNormalizer.extract_words("\n".join(orig)),
            TextNormalizer.extract_words("\n".join(ext)),
            mismatches
        )

        from app.originality.models import PageOriginalityResult, OriginalityReport, VerificationType
        page_res = PageOriginalityResult(
            page=1,
            orig_word_count=len("\n".join(orig).split()),
            extracted_word_count=len("\n".join(ext).split()),
            orig_char_count=len("\n".join(orig)),
            extracted_char_count=len("\n".join(ext)),
            accuracy=acc,
            status=status,
            verification_type=VerificationType.TEXT_BASED,
            mismatches=mismatches,
            orig_lines=orig,
            extracted_lines=ext,
            line_diffs=line_diffs
        )

        report = OriginalityReport(
            report_id="test-rep-12345",
            original_filename="sample.pdf",
            extracted_filename="sample.txt",
            file_type="pdf",
            timestamp="2026-10-01 12:00:00",
            overall_accuracy=acc,
            verification_status=status,
            total_pages=1,
            passed_pages=1 if status == StatusType.PASS else 0,
            warning_pages=1 if status == StatusType.WARNING else 0,
            error_pages=1 if status == StatusType.ERROR else 0,
            total_orig_words=page_res.orig_word_count,
            total_extracted_words=page_res.extracted_word_count,
            missing_words=0,
            extra_words=0,
            changed_words=1,
            character_errors=0,
            number_mismatches=1,
            punctuation_mismatches=0,
            reading_order_issues=0,
            pages=[page_res],
            summary_notes=["Test report note"]
        )

        json_out = ReportGenerator.generate_json(report)
        self.assertIn("test-rep-12345", json_out)
        self.assertIn("NUMBER_MISMATCH", json_out)

        csv_out = ReportGenerator.generate_csv(report)
        self.assertIn("ORIGINALITY & EXTRACTION ACCURACY", csv_out)
        self.assertIn("Page 1", csv_out)

        pdf_bytes = ReportGenerator.generate_pdf(report)
        self.assertTrue(len(pdf_bytes) > 500)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))


if __name__ == '__main__':
    unittest.main()
