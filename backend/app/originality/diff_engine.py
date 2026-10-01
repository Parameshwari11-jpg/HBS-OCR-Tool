import re
import difflib
import uuid
from typing import List, Dict, Any, Tuple, Optional
from app.originality.models import (
    DifferenceType,
    SeverityLevel,
    MismatchItem,
    CharacterDifference,
    LineDiffItem,
)
from app.originality.normalizer import TextNormalizer


class DiffEngine:
    """
    Intelligent line-by-line, word-level, and character-level comparison engine.
    Detects missing text, extra text, changed words, number discrepancies,
    OCR character dropouts, punctuation shifts, and reading order anomalies.
    """

    @classmethod
    def compare_page_lines(
        cls,
        orig_lines: List[str],
        ext_lines: List[str],
        page_num: int,
        confidence: Optional[float] = None
    ) -> Tuple[List[LineDiffItem], List[MismatchItem]]:
        """
        Performs aligned line-by-line comparison of original and extracted lines for a page.
        """
        line_diffs: List[LineDiffItem] = []
        mismatches: List[MismatchItem] = []

        # If both are empty: perfect match
        if not orig_lines and not ext_lines:
            return line_diffs, mismatches

        # Use normalized lines for sequence alignment to prevent trivial punctuation spaces from breaking matches
        norm_orig = [TextNormalizer.normalize_line(l) for l in orig_lines]
        norm_ext = [TextNormalizer.normalize_line(l) for l in ext_lines]
        matcher = difflib.SequenceMatcher(None, norm_orig, norm_ext)
        opcodes = matcher.get_opcodes()

        # Check for reading order transposition: detect if matching chunks are reversed
        matching_blocks = matcher.get_matching_blocks()
        cls._detect_reading_order_issues(orig_lines, ext_lines, matching_blocks, page_num, mismatches)

        mismatch_counter = 1

        for tag, i1, i2, j1, j2 in opcodes:
            if tag == 'equal':
                for o_idx, e_idx in zip(range(i1, i2), range(j1, j2)):
                    line_diffs.append(LineDiffItem(
                        orig_line_num=o_idx + 1,
                        ext_line_num=e_idx + 1,
                        tag='equal',
                        orig_line=orig_lines[o_idx],
                        extracted_line=ext_lines[e_idx],
                        diff_type=DifferenceType.EXACT_MATCH,
                        mismatches=[]
                    ))

            elif tag == 'delete':
                # Lines exist in original but were omitted in extracted text
                for o_idx in range(i1, i2):
                    line_txt = orig_lines[o_idx]
                    mm = MismatchItem(
                        id=f"mm_p{page_num}_{mismatch_counter}",
                        page=page_num,
                        line=o_idx + 1,
                        location=f"Page {page_num}, Line {o_idx + 1}",
                        orig_text=line_txt,
                        extracted_text="",
                        difference=f"Omitted: '{line_txt}'",
                        diff_type=DifferenceType.MISSING_TEXT,
                        severity=SeverityLevel.HIGH if any(c.isalnum() for c in line_txt) else SeverityLevel.LOW,
                        confidence=confidence
                    )
                    mismatches.append(mm)
                    mismatch_counter += 1

                    line_diffs.append(LineDiffItem(
                        orig_line_num=o_idx + 1,
                        ext_line_num=None,
                        tag='delete',
                        orig_line=line_txt,
                        extracted_line="",
                        diff_type=DifferenceType.MISSING_TEXT,
                        mismatches=[mm]
                    ))

            elif tag == 'insert':
                # Lines exist in extracted text but were not in original
                for e_idx in range(j1, j2):
                    line_txt = ext_lines[e_idx]
                    mm = MismatchItem(
                        id=f"mm_p{page_num}_{mismatch_counter}",
                        page=page_num,
                        line=e_idx + 1,
                        location=f"Page {page_num}, Line {e_idx + 1} (Extracted)",
                        orig_text="",
                        extracted_text=line_txt,
                        difference=f"Extra text: '{line_txt}'",
                        diff_type=DifferenceType.EXTRA_TEXT,
                        severity=SeverityLevel.MEDIUM if any(c.isalnum() for c in line_txt) else SeverityLevel.LOW,
                        confidence=confidence
                    )
                    mismatches.append(mm)
                    mismatch_counter += 1

                    line_diffs.append(LineDiffItem(
                        orig_line_num=None,
                        ext_line_num=e_idx + 1,
                        tag='insert',
                        orig_line="",
                        extracted_line=line_txt,
                        diff_type=DifferenceType.EXTRA_TEXT,
                        mismatches=[mm]
                    ))

            elif tag == 'replace':
                # Deep word and character comparison for substituted lines
                orig_sub = orig_lines[i1:i2]
                ext_sub = ext_lines[j1:j2]

                max_len = max(len(orig_sub), len(ext_sub))
                for k in range(max_len):
                    o_line = orig_sub[k] if k < len(orig_sub) else ""
                    e_line = ext_sub[k] if k < len(ext_sub) else ""
                    o_num = (i1 + k + 1) if k < len(orig_sub) else None
                    e_num = (j1 + k + 1) if k < len(ext_sub) else None

                    # If normalized lines are identical, it is an exact match!
                    if o_line and e_line and TextNormalizer.normalize_line(o_line) == TextNormalizer.normalize_line(e_line):
                        line_diffs.append(LineDiffItem(
                            orig_line_num=o_num,
                            ext_line_num=e_num,
                            tag='equal',
                            orig_line=o_line,
                            extracted_line=e_line,
                            diff_type=DifferenceType.EXACT_MATCH,
                            mismatches=[]
                        ))
                        continue

                    line_mms = cls._compare_line_pair(
                        o_line,
                        e_line,
                        page_num=page_num,
                        line_num=o_num or e_num or 1,
                        start_counter=mismatch_counter,
                        confidence=confidence
                    )
                    mismatches.extend(line_mms)
                    mismatch_counter += len(line_mms)

                    primary_diff_type = line_mms[0].diff_type if line_mms else DifferenceType.WORD_MISMATCH
                    line_diffs.append(LineDiffItem(
                        orig_line_num=o_num,
                        ext_line_num=e_num,
                        tag='replace',
                        orig_line=o_line,
                        extracted_line=e_line,
                        diff_type=primary_diff_type,
                        mismatches=line_mms
                    ))

        return line_diffs, mismatches

    @classmethod
    def _compare_line_pair(
        cls,
        orig_line: str,
        ext_line: str,
        page_num: int,
        line_num: int,
        start_counter: int,
        confidence: Optional[float] = None
    ) -> List[MismatchItem]:
        """
        Compares an original line with an extracted line at word and character levels.
        """
        mismatches: List[MismatchItem] = []
        counter = start_counter

        # If lines match when normalized, zero mismatches!
        if TextNormalizer.normalize_line(orig_line) == TextNormalizer.normalize_line(ext_line):
            return []

        # 1. Check for Numbers Mismatch (High Severity)
        orig_numbers = TextNormalizer.extract_numbers(orig_line)
        ext_numbers = TextNormalizer.extract_numbers(ext_line)

        if orig_numbers != ext_numbers:
            # Check which numbers are missing or changed
            diff_nums = [f"{o} → {e}" for o, e in zip(orig_numbers, ext_numbers) if o != e]
            if len(orig_numbers) > len(ext_numbers):
                diff_nums.extend([f"Missing: '{n}'" for n in orig_numbers[len(ext_numbers):]])
            elif len(ext_numbers) > len(orig_numbers):
                diff_nums.extend([f"Extra: '{n}'" for n in ext_numbers[len(orig_numbers):]])

            diff_desc = ", ".join(diff_nums) if diff_nums else f"{orig_numbers} ≠ {ext_numbers}"
            mismatches.append(MismatchItem(
                id=f"mm_p{page_num}_{counter}",
                page=page_num,
                line=line_num,
                location=f"Page {page_num}, Line {line_num}",
                orig_text=orig_line,
                extracted_text=ext_line,
                difference=diff_desc,
                diff_type=DifferenceType.NUMBER_MISMATCH,
                severity=SeverityLevel.HIGH,
                confidence=confidence
            ))
            counter += 1

        # 2. Tokenize words and perform Word-Level Alignment
        orig_words = orig_line.split()
        ext_words = ext_line.split()

        w_matcher = difflib.SequenceMatcher(None, orig_words, ext_words)
        for w_tag, wi1, wi2, wj1, wj2 in w_matcher.get_opcodes():
            if w_tag == 'equal':
                continue

            elif w_tag == 'replace':
                o_chunk = orig_words[wi1:wi2]
                e_chunk = ext_words[wj1:wj2]

                # Pairwise word character comparison for OCR anomalies
                for ow, ew in zip(o_chunk, e_chunk):
                    # If this word pair was already covered by number mismatch, skip duplicate
                    if ow in orig_numbers and ew in ext_numbers and ow != ew:
                        continue

                    char_diffs = cls._compare_characters(ow, ew)
                    is_only_case_or_punct = (ow.lower() == ew.lower()) or (re.sub(r'\W', '', ow) == re.sub(r'\W', '', ew))
                    
                    diff_type = DifferenceType.WORD_MISMATCH
                    if char_diffs and len(char_diffs) <= 2 and abs(len(ow) - len(ew)) <= 1:
                        diff_type = DifferenceType.CHARACTER_MISMATCH

                    severity = SeverityLevel.LOW if is_only_case_or_punct else SeverityLevel.MEDIUM

                    mismatches.append(MismatchItem(
                        id=f"mm_p{page_num}_{counter}",
                        page=page_num,
                        line=line_num,
                        location=f"Page {page_num}, Line {line_num}",
                        orig_text=ow,
                        extracted_text=ew,
                        difference=f"'{ow}' → '{ew}'",
                        diff_type=diff_type,
                        severity=severity,
                        confidence=confidence,
                        char_diffs=char_diffs
                    ))
                    counter += 1

                # If word count differs in the chunk:
                if len(o_chunk) > len(e_chunk):
                    for ow in o_chunk[len(e_chunk):]:
                        mismatches.append(MismatchItem(
                            id=f"mm_p{page_num}_{counter}",
                            page=page_num,
                            line=line_num,
                            location=f"Page {page_num}, Line {line_num}",
                            orig_text=ow,
                            extracted_text="",
                            difference=f"Missing word: '{ow}'",
                            diff_type=DifferenceType.MISSING_TEXT,
                            severity=SeverityLevel.MEDIUM,
                            confidence=confidence
                        ))
                        counter += 1
                elif len(e_chunk) > len(o_chunk):
                    for ew in e_chunk[len(o_chunk):]:
                        mismatches.append(MismatchItem(
                            id=f"mm_p{page_num}_{counter}",
                            page=page_num,
                            line=line_num,
                            location=f"Page {page_num}, Line {line_num}",
                            orig_text="",
                            extracted_text=ew,
                            difference=f"Extra word: '{ew}'",
                            diff_type=DifferenceType.EXTRA_TEXT,
                            severity=SeverityLevel.MEDIUM,
                            confidence=confidence
                        ))
                        counter += 1

            elif w_tag == 'delete':
                for ow in orig_words[wi1:wi2]:
                    mismatches.append(MismatchItem(
                        id=f"mm_p{page_num}_{counter}",
                        page=page_num,
                        line=line_num,
                        location=f"Page {page_num}, Line {line_num}",
                        orig_text=ow,
                        extracted_text="",
                        difference=f"Missing word: '{ow}'",
                        diff_type=DifferenceType.MISSING_TEXT,
                        severity=SeverityLevel.MEDIUM,
                        confidence=confidence
                    ))
                    counter += 1

            elif w_tag == 'insert':
                for ew in ext_words[wj1:wj2]:
                    mismatches.append(MismatchItem(
                        id=f"mm_p{page_num}_{counter}",
                        page=page_num,
                        line=line_num,
                        location=f"Page {page_num}, Line {line_num}",
                        orig_text="",
                        extracted_text=ew,
                        difference=f"Extra word: '{ew}'",
                        diff_type=DifferenceType.EXTRA_TEXT,
                        severity=SeverityLevel.MEDIUM,
                        confidence=confidence
                    ))
                    counter += 1

        # Fallback if no specific word mismatch was generated but lines are distinct
        if not mismatches and orig_line.strip() != ext_line.strip():
            mismatches.append(MismatchItem(
                id=f"mm_p{page_num}_{counter}",
                page=page_num,
                line=line_num,
                location=f"Page {page_num}, Line {line_num}",
                orig_text=orig_line,
                extracted_text=ext_line,
                difference=f"Line difference",
                diff_type=DifferenceType.WORD_MISMATCH,
                severity=SeverityLevel.LOW,
                confidence=confidence
            ))

        return mismatches

    @classmethod
    def _compare_characters(cls, orig_word: str, ext_word: str) -> List[CharacterDifference]:
        """
        Performs character-by-character alignment to locate missing or erroneous letters (e.g. Accessibility vs Accessibilty).
        """
        char_diffs: List[CharacterDifference] = []
        if orig_word == ext_word:
            return char_diffs

        c_matcher = difflib.SequenceMatcher(None, orig_word, ext_word)
        for c_tag, ci1, ci2, cj1, cj2 in c_matcher.get_opcodes():
            if c_tag == 'delete':
                missing_chars = orig_word[ci1:ci2]
                for idx, ch in enumerate(missing_chars):
                    char_diffs.append(CharacterDifference(
                        diff_type="missing_char",
                        char=ch,
                        position=ci1 + idx + 1,
                        orig_word=orig_word,
                        extracted_word=ext_word
                    ))
            elif c_tag == 'insert':
                extra_chars = ext_word[cj1:cj2]
                for idx, ch in enumerate(extra_chars):
                    char_diffs.append(CharacterDifference(
                        diff_type="extra_char",
                        char=ch,
                        position=cj1 + idx + 1,
                        orig_word=orig_word,
                        extracted_word=ext_word
                    ))
            elif c_tag == 'replace':
                old_chars = orig_word[ci1:ci2]
                new_chars = ext_word[cj1:cj2]
                char_diffs.append(CharacterDifference(
                    diff_type="changed_char",
                    char=f"{old_chars}→{new_chars}",
                    position=ci1 + 1,
                    orig_word=orig_word,
                    extracted_word=ext_word
                ))

        return char_diffs

    @classmethod
    def _detect_reading_order_issues(
        cls,
        orig_lines: List[str],
        ext_lines: List[str],
        matching_blocks: List[Any],
        page_num: int,
        mismatches: List[MismatchItem]
    ):
        """
        Identifies non-monotonic block matches where text blocks appear inverted in sequence.
        """
        if len(matching_blocks) <= 2:
            return

        last_j = -1
        for block in matching_blocks:
            if block.size < 2:  # ignore single trivial matches
                continue
            if block.b < last_j:
                # Inversion detected in extracted target index
                orig_sample = orig_lines[block.a] if block.a < len(orig_lines) else ""
                ext_sample = ext_lines[block.b] if block.b < len(ext_lines) else ""
                mismatches.append(MismatchItem(
                    id=f"mm_p{page_num}_ro_{block.a}",
                    page=page_num,
                    line=block.a + 1,
                    location=f"Page {page_num}, Line {block.a + 1}",
                    orig_text=orig_sample,
                    extracted_text=ext_sample,
                    difference="Possible reading-order transposition: text appeared out of visual order",
                    diff_type=DifferenceType.READING_ORDER,
                    severity=SeverityLevel.MEDIUM
                ))
            last_j = max(last_j, block.b + block.size)
