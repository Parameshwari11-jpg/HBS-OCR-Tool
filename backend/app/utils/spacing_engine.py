"""
Generic Text Boundary and Spacing Engine.

Solves the token-boundary spacing problem when merging multiple text fragments,
such as when users or document parsers merge adjacent <span> tags or runs.

Core Principles:
1. Purely generic and document-independent: NO hardcoded words, phrases, or documents.
2. Tiered decision pipeline:
   - Level 1: Preserves existing whitespace (trailing/leading spaces or tabs).
   - Level 2: Punctuation and typographical boundary rules (commas, periods, brackets, apostrophes).
   - Level 3: Orthographic and pattern boundary rules (case transitions, numbers, symbols).
   - Level 4: Vocabulary and compound word analysis (valid standalone words vs compound check).
3. Works for arbitrary sequences: T1 + T2 + ... + Tn.
"""

import os
import re
from typing import List, Sequence, Optional, Set, Tuple

# Pre-compiled regex patterns for Level 2 & Level 3 rules
PUNCT_NO_SPACE_BEFORE = set(".,;:!?)]}%'\"”’»")
PUNCT_NO_SPACE_AFTER = set("([{‘“«$#@")
MATH_OPERATORS = set("+-−=*/<>≤≥≠±×÷")

class SpacingEngine:
    """
    Generic multi-level token boundary spacing engine.
    """
    _instance: Optional['SpacingEngine'] = None
    _vocabulary: Optional[Set[str]] = None
    _common_words: Optional[Set[str]] = None

    def __init__(self):
        self._ensure_vocab_loaded()

    @classmethod
    def get_instance(cls) -> 'SpacingEngine':
        if cls._instance is None:
            cls._instance = SpacingEngine()
        return cls._instance

    @classmethod
    def _ensure_vocab_loaded(cls):
        if cls._vocabulary is not None:
            return

        cls._vocabulary = set()
        cls._common_words = set()

        # Load vocabularies from disk if available
        base_dir = os.path.dirname(__file__)
        words_path = os.path.join(base_dir, "words_alpha.txt")
        common_path = os.path.join(base_dir, "common_words.txt")

        if os.path.exists(words_path):
            try:
                with open(words_path, "r", encoding="utf-8") as f:
                    cls._vocabulary = set(line.strip().lower() for line in f if line.strip())
            except Exception:
                pass

        if os.path.exists(common_path):
            try:
                with open(common_path, "r", encoding="utf-8") as f:
                    cls._common_words = set(line.strip().lower() for line in f if line.strip())
            except Exception:
                pass

    def is_valid_word(self, word: str) -> bool:
        """Checks if a normalized token is a known word in vocabulary."""
        if not word:
            return False
        w = word.lower()
        if self._vocabulary and w in self._vocabulary:
            return True
        if self._common_words and w in self._common_words:
            return True
        return False

    def is_common_word(self, word: str) -> bool:
        """Checks if a normalized token is among common usage words."""
        if not word:
            return False
        w = word.lower()
        if self._common_words and w in self._common_words:
            return True
        return False

    def should_insert_space(
        self,
        left_raw: str,
        right_raw: str,
        coord_gap: Optional[float] = None,
        font_size: Optional[float] = None
    ) -> bool:
        """
        Evaluates whether a space should be inserted between left_raw and right_raw.
        Multi-level decision process:
        - Level 1: Original whitespace inspection
        - Level 2: Punctuation and typographical rules
        - Level 3: Orthographic and pattern boundary rules
        - Level 4: Vocabulary and compound word analysis
        """
        # Level 1: Preserve original whitespace
        if left_raw.endswith(" ") or left_raw.endswith("\t") or left_raw.endswith("\n"):
            return False  # Already contains whitespace
        if right_raw.startswith(" ") or right_raw.startswith("\t") or right_raw.startswith("\n"):
            return False  # Already contains whitespace

        left = left_raw.strip()
        right = right_raw.strip()

        if not left or not right:
            return False

        # Level 2: Punctuation and Typography Rules
        last_char = left[-1]
        first_char = right[0]

        # Contraction / possessive suffix e.g. "word" + "'s", "don" + "'t"
        if right.startswith("'") or right.startswith("’"):
            if len(right) <= 3 and right[1:].isalpha():
                return False

        # Hyphen rules e.g. "semi-" + "annual" or "multi" + "-purpose"
        if last_char in "-–—" or first_char in "-–—":
            return False

        # Left ends with opening bracket/symbol e.g. "(" + "word" -> "(word"
        if last_char in PUNCT_NO_SPACE_AFTER:
            return False

        # Right starts with closing bracket/punctuation e.g. "word" + "," -> "word,"
        if first_char in PUNCT_NO_SPACE_BEFORE:
            return False

        # Physical coordinate gap check (if layout coordinates are available)
        # Checked here after immediate attachment punctuation/brackets are ruled out
        if coord_gap is not None and font_size is not None and font_size > 0:
            # Typical space glyph width is between 0.20 and 0.35 of font size
            # If gap between boxes >= 0.22 * font_size, physical space definitely existed
            if coord_gap >= (0.22 * font_size):
                return True
            # Negative or near-zero gap (< 0.05 * font_size) suggests connected or overlapping letters
            if coord_gap < (0.05 * font_size):
                return False

        # Left ends with sentence-ending or clause punctuation e.g. "word." + "Next" -> "word. Next"
        if last_char in ".,;:!?»)]}":
            # Exception: decimal point in numbers like "3." + "14"
            if last_char == "." and left[:-1].isdigit() and right.isdigit():
                return False
            # Exception: abbreviations/acronyms like "U." + "S." + "A."
            if last_char == "." and len(left) <= 2 and len(right) <= 2 and left.isupper() and right.isupper():
                return False
            return True

        # Math / arithmetic operators e.g. "a" + "+" + "b"
        if last_char in MATH_OPERATORS or first_char in MATH_OPERATORS:
            return True

        # Extract the boundary word/token from each fragment:
        # e.g. "Ms. Harwood wrote the grammar" -> boundary word is "grammar"
        # e.g. "presentations, created activities for" -> boundary word is "presentations"
        # If fragment is a single word, it equals that word.
        left_tokens = re.findall(r'[a-zA-Z0-9]+', left)
        right_tokens = re.findall(r'[a-zA-Z0-9]+', right)
        
        b_left = left_tokens[-1] if left_tokens else left
        b_right = right_tokens[0] if right_tokens else right

        # Level 3: Orthographic & Character Class Transitions on boundary tokens

        # Letters and digits:
        # e.g. "Chapter" + "5" -> "Chapter 5"
        if b_left.isalpha() and b_right.isdigit():
            return True

        # e.g. "Page" + "IV" -> "Page IV"
        if b_left.isalpha() and b_right.isalnum() and b_right.isupper() and len(b_right) <= 4 and not b_left.isupper():
            return True

        # Digit and letter / unit:
        # e.g. "100" + "meters", "25" + "books" -> space
        # e.g. "100" + "px", "5" + "kg", "10" + "th" -> no space if unit/suffix
        if b_left.isdigit() and b_right.isalpha():
            units_and_suffixes = {
                "th", "st", "nd", "rd",
                "px", "pt", "em", "rem", "vh", "vw", "%",
                "mm", "cm", "km", "kg", "mg", "ml", "ms", "hz", "khz", "mhz", "ghz"
            }
            if b_right.lower() in units_and_suffixes:
                return False
            return True

        # Capitalization patterns:
        # Case 1: TitleCase / Capitalized + TitleCase / Capitalized
        # e.g. "Contributing" + "Writers" -> Space
        # e.g. "Contrbuting" + "Witers" -> Space (works even with OCR misspellings!)
        # e.g. "United" + "States" -> Space
        if b_left[0].isupper() and b_right[0].isupper() and not b_left.isupper() and not b_right.isupper():
            return True

        # Case 2: ALL CAPS word + ALL CAPS word
        # e.g. "COMMON" + "OPTIONS" -> Space
        # e.g. "SECTION" + "FIVE" -> Space
        if b_left.isupper() and b_right.isupper() and len(b_left) > 1 and len(b_right) > 1:
            return True

        # Case 3: lowercase + Capital (camelCase boundary)
        if b_left.islower() and b_right[0].isupper() and len(b_right) > 1 and b_right[1:].islower():
            return True

        # Level 4: Vocabulary and Compound Word Analysis
        # Both boundary tokens are alphabetic
        if b_left.isalpha() and b_right.isalpha():
            left_clean = b_left.lower()
            right_clean = b_right.lower()
            combined = left_clean + right_clean

            left_is_word = self.is_valid_word(left_clean)
            right_is_word = self.is_valid_word(right_clean)
            combined_is_word = self.is_valid_word(combined)

            # Prefixes that form closed single words (e.g. "super" + "script" -> "superscript",
            # "inter" + "national" -> "international", "pre" + "requisite" -> "prerequisite")
            prefixes = {
                "un", "re", "in", "im", "dis", "en", "em", "non", "over", "mis",
                "sub", "pre", "inter", "fore", "de", "trans", "super", "semi",
                "anti", "mid", "under", "micro", "macro", "auto", "co"
            }
            if left_clean in prefixes and combined_is_word:
                return False

            # Common English suffixes
            suffixes = {
                "ing", "ed", "tion", "sion", "able", "ible", "ment", "ness",
                "less", "ful", "ity", "ous", "ship", "hood", "ward", "wise"
            }
            if right_clean in suffixes and combined_is_word:
                return False

            # If combined is an established compound word (like "everybody", "lifestyle", "something")
            # AND either fragment is NOT commonly standalone OR combined is much more unified
            if combined_is_word and not (b_left[0].isupper() and b_right[0].isupper()):
                # If one of them is NOT a standalone word, definitely combine without space!
                # e.g. "docu" + "ment" -> "document"
                if not left_is_word or not right_is_word:
                    return False

                # If both are valid standalone words, check if combined is a recognized closed compound
                closed_compounds = {
                    "everybody", "everyone", "everything", "everywhere",
                    "somebody", "someone", "something", "somewhere",
                    "anybody", "anyone", "anything", "anywhere",
                    "nobody", "nothing", "nowhere",
                    "into", "onto", "upon", "within", "without", "throughout",
                    "cannot", "maybe", "already", "almost", "always",
                    "meanwhile", "furthermore", "moreover", "nevertheless",
                    "lifestyle", "database", "filename", "network", "software",
                    "hardware", "keyboard", "screenshot", "setup", "textbox",
                    "toolbar", "scrollbar", "checkbox", "dropdown"
                }
                if combined in closed_compounds:
                    return False

            # If both fragments are valid standalone words and combined is NOT a valid word
            # e.g. "Contributing" + "Writers" -> "contributingwriters" is NOT a word
            # -> definitely insert space!
            if left_is_word and right_is_word and not combined_is_word:
                return True

            # If left is not a word and right is a word, or vice versa, and combined IS a word
            # e.g. "sy" + "stem" -> "system" -> no space
            if combined_is_word and (not left_is_word or not right_is_word):
                return False

            # Default for two standard words in sequence
            if left_is_word and right_is_word:
                return True

        # Fallback: if both boundary tokens are alphanumeric, separate with a space by default
        if b_left.isalnum() and b_right.isalnum():
            return True

        return False

    def merge_tokens(
        self,
        fragments: Sequence[str],
        coord_gaps: Optional[Sequence[Optional[float]]] = None,
        font_sizes: Optional[Sequence[Optional[float]]] = None
    ) -> str:
        """
        Merges an arbitrary sequence of text fragments T1, T2, ..., Tn
        evaluating every boundary independently.
        """
        if not fragments:
            return ""
        if len(fragments) == 1:
            return fragments[0]

        result_parts = [fragments[0]]

        for i in range(1, len(fragments)):
            prev_token = result_parts[-1]
            curr_token = fragments[i]

            gap = coord_gaps[i - 1] if coord_gaps and i - 1 < len(coord_gaps) else None
            fs = font_sizes[i - 1] if font_sizes and i - 1 < len(font_sizes) else None

            if self.should_insert_space(prev_token, curr_token, coord_gap=gap, font_size=fs):
                result_parts.append(" ")
            result_parts.append(curr_token)

        return "".join(result_parts)

# Singleton helper functions for clean integration
_engine = SpacingEngine.get_instance()

def should_insert_space(
    left: str,
    right: str,
    coord_gap: Optional[float] = None,
    font_size: Optional[float] = None
) -> bool:
    return _engine.should_insert_space(left, right, coord_gap=coord_gap, font_size=font_size)

def merge_tokens(
    fragments: Sequence[str],
    coord_gaps: Optional[Sequence[Optional[float]]] = None,
    font_sizes: Optional[Sequence[Optional[float]]] = None
) -> str:
    return _engine.merge_tokens(fragments, coord_gaps=coord_gaps, font_sizes=font_sizes)
