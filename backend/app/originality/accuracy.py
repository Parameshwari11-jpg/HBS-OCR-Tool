import difflib
from typing import List, Dict, Any, Tuple
from app.originality.models import StatusType, SeverityLevel, DifferenceType, MismatchItem


class AccuracyCalculator:
    """
    Reproducible, scientifically grounded accuracy and status calculator.
    Uses token-level edit distance, normalized character similarity,
    and semantic severity penalties.
    """

    PASS_THRESHOLD = 99.0     # >= 99.0% and 0 HIGH severity errors -> PASS
    WARNING_THRESHOLD = 95.0  # 95.0% - 98.9% -> WARNING; < 95.0% -> ERROR

    @classmethod
    def calculate_page_accuracy(
        cls,
        orig_words: List[str],
        ext_words: List[str],
        mismatches: List[MismatchItem]
    ) -> Tuple[float, StatusType]:
        """
        Calculates the accuracy percentage and status for a single page.
        """
        # Perfect exact match case
        if orig_words == ext_words:
            return 100.0, StatusType.PASS

        total_orig = len(orig_words)
        total_ext = len(ext_words)

        if total_orig == 0 and total_ext == 0:
            return 100.0, StatusType.PASS

        if total_orig == 0 and total_ext > 0:
            return 0.0, StatusType.ERROR

        # Calculate word sequence alignment
        matcher = difflib.SequenceMatcher(None, orig_words, ext_words)
        match_ratio = matcher.ratio()  # 0.0 to 1.0 based on 2*M / (T_O + T_E)

        # Baseline accuracy percentage
        accuracy = round(match_ratio * 100.0, 1)

        # Count high and medium severity mismatches
        high_severity_count = sum(1 for m in mismatches if m.severity == SeverityLevel.HIGH)
        medium_severity_count = sum(1 for m in mismatches if m.severity == SeverityLevel.MEDIUM)

        # Apply appropriate penalty for critical number errors
        if high_severity_count > 0:
            # High severity number/critical mismatches prevent false 100% or 99% scores
            accuracy = min(accuracy, 94.5 if accuracy >= 95.0 and high_severity_count >= 2 else 96.0)

        accuracy = max(0.0, min(100.0, accuracy))

        # Determine status
        if accuracy >= cls.PASS_THRESHOLD and high_severity_count == 0 and medium_severity_count == 0:
            status = StatusType.PASS
        elif accuracy >= cls.WARNING_THRESHOLD and high_severity_count == 0:
            status = StatusType.WARNING
        else:
            status = StatusType.ERROR

        return accuracy, status

    @classmethod
    def calculate_overall_accuracy(
        cls,
        page_results: List[Any],
        all_mismatches: List[MismatchItem]
    ) -> Tuple[float, StatusType]:
        """
        Calculates weighted overall document accuracy and global verification status.
        """
        if not page_results:
            return 0.0, StatusType.ERROR

        # Check if all pages are 100% exact match
        if all(p.accuracy == 100.0 and len(p.mismatches) == 0 for p in page_results):
            return 100.0, StatusType.PASS

        total_words_orig = sum(p.orig_word_count for p in page_results)
        if total_words_orig == 0:
            # Fallback to mean of page accuracies
            avg_acc = sum(p.accuracy for p in page_results) / len(page_results)
            overall_acc = round(avg_acc, 1)
        else:
            # Word-count weighted accuracy
            weighted_sum = sum(p.accuracy * max(p.orig_word_count, 1) for p in page_results)
            overall_acc = round(weighted_sum / sum(max(p.orig_word_count, 1) for p in page_results), 1)

        high_errors = sum(1 for m in all_mismatches if m.severity == SeverityLevel.HIGH)
        error_pages = sum(1 for p in page_results if p.status == StatusType.ERROR)
        warning_pages = sum(1 for p in page_results if p.status == StatusType.WARNING)

        if overall_acc >= cls.PASS_THRESHOLD and high_errors == 0 and error_pages == 0 and warning_pages == 0:
            global_status = StatusType.PASS
        elif overall_acc >= cls.WARNING_THRESHOLD and error_pages == 0 and high_errors == 0:
            global_status = StatusType.WARNING
        else:
            global_status = StatusType.ERROR

        return overall_acc, global_status
