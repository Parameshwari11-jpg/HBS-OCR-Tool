"""
Centralized language configuration for the OCR backend.

Mapping from the language code sent by the frontend to the PaddleOCR language string.

To add a new language:
  1. Add an entry to SUPPORTED_LANGUAGES.
  2. That's it — the OCR engine, extraction service, and API all pick it up automatically.

PaddleOCR supported lang strings:
  https://paddlepaddle.github.io/PaddleOCR/latest/en/ppocr/blog/multi_languages.html
"""

from typing import Dict

# Maps the frontend language code → PaddleOCR lang string
SUPPORTED_LANGUAGES: Dict[str, str] = {
    "en": "en",
    "fr": "fr",
    "es": "es",
    # --- Add more languages below ---
    # "de": "german",
    # "it": "it",
    # "hi": "hi",
    # "ta": "ta",
}

DEFAULT_LANGUAGE = "en"


def get_ocr_lang(code: str) -> str:
    """
    Return the PaddleOCR language string for a given frontend language code.
    Falls back to DEFAULT_LANGUAGE if the code is unknown.
    """
    if not code or code not in SUPPORTED_LANGUAGES:
        return SUPPORTED_LANGUAGES[DEFAULT_LANGUAGE]
    return SUPPORTED_LANGUAGES[code]
