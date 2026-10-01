import re
import unicodedata
from typing import List, Tuple


class TextNormalizer:
    """
    Intelligent text normalization for extraction accuracy and originality verification.
    Normalizes typographic artifacts, line endings, and whitespace while strictly
    preserving meaningful content, numbers, math symbols, and punctuation.
    """

    # Quotation mark variants
    DOUBLE_QUOTES = re.compile(r'[“”„«»″″]')
    SINGLE_QUOTES = re.compile(r'[‘’‚‛′′`]')

    # Dash variants (normalize to standard hyphen for comparison, while preserving minus/math if needed)
    DASHES = re.compile(r'[—–‒―]')

    # Zero-width & non-standard spaces
    SPECIAL_SPACES = re.compile(r'[\u00a0\u1680\u2000-\u200b\u202f\u205f\u3000\ufeff]')

    @classmethod
    def normalize_text(cls, text: str) -> str:
        """
        Normalizes a multi-line document string.
        """
        if not text:
            return ""

        # 1. Standardize line endings (Windows \r\n, Mac \r -> Unix \n)
        s = text.replace('\r\n', '\n').replace('\r', '\n')

        # Process each line with full normalization
        lines = []
        for line in s.split('\n'):
            cleaned_line = cls.normalize_line(line)
            lines.append(cleaned_line)

        # Join and collapse 3+ consecutive newlines into double newlines
        result = '\n'.join(lines)
        result = re.sub(r'\n{3,}', '\n\n', result).strip()
        return result

    @classmethod
    def normalize_line(cls, line: str) -> str:
        """
        Normalizes an individual line, eliminating typographic differences like
        spaces before punctuation, spaces around brackets, and quote variants.
        """
        if not line:
            return ""
        s = unicodedata.normalize('NFKC', line)
        s = cls.SPECIAL_SPACES.sub(' ', s)
        s = cls.DOUBLE_QUOTES.sub('"', s)
        s = cls.SINGLE_QUOTES.sub("'", s)
        s = cls.DASHES.sub('-', s)
        # Strip spaces before standard punctuation (: , . ; ! ?)
        s = re.sub(r'\s+([,.:;?!])', r'\1', s)
        # Normalize spaces inside parentheses and brackets
        s = re.sub(r'\(\s+', '(', s)
        s = re.sub(r'\s+\)', ')', s)
        # Normalize inequality symbols (≠ -> !=, ≤ -> <=, ≥ -> >=)
        s = s.replace('≠', '!=').replace('≤', '<=').replace('≥', '>=')
        # Normalize spaces around division/fraction slashes
        s = re.sub(r'\s*/\s*', '/', s)
        # Normalize/strip leading bullet markers and font replacement glyphs
        s = re.sub(r'^[\u2022\u25cf\u25aa\u25ab\u2023\uf0b7\ufffd\·\*\-]\s*', '', s)
        # Collapse multiple internal spaces
        s = re.sub(r'[ \t]+', ' ', s).strip()
        return s

    @classmethod
    def get_lines(cls, text: str, keep_empty: bool = False) -> List[str]:
        """
        Splits normalized text into a list of clean lines.
        """
        norm = cls.normalize_text(text)
        if not norm:
            return []
        lines = [cls.normalize_line(l) for l in norm.split('\n')]
        if not keep_empty:
            lines = [l for l in lines if l]
        return lines

    @classmethod
    def extract_words(cls, text: str) -> List[str]:
        """
        Extracts words while preserving numbers, hyphenated words, and contractions.
        """
        if not text:
            return []
        norm = cls.normalize_text(text)
        # Tokenize by whitespace, preserving tokens with attached punctuation separated
        tokens = re.findall(r'[a-zA-Z0-9_\-\+\*\/\.\,\:\;\(\)≠≤≥±]+|[^\s\w]', norm)
        return [t for t in tokens if t.strip()]

    @classmethod
    def extract_numbers(cls, text: str) -> List[str]:
        """
        Extracts all numeric tokens (integers, decimals, percentages, dates) from text.
        """
        if not text:
            return []
        # Matches numbers like 500, 3.14, 98.7%, 2026, 1/2
        return re.findall(r'\b\d+(?:[\.,/]\d+)*(?:%|[a-zA-Z]{1,2}\b)?', text)
