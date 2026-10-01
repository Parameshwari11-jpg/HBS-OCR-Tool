from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class DifferenceType(str, Enum):
    EXACT_MATCH = "EXACT_MATCH"
    NUMBER_MISMATCH = "NUMBER_MISMATCH"
    WORD_MISMATCH = "WORD_MISMATCH"
    CHARACTER_MISMATCH = "CHARACTER_MISMATCH"
    MISSING_TEXT = "MISSING_TEXT"
    EXTRA_TEXT = "EXTRA_TEXT"
    READING_ORDER = "READING_ORDER"
    PUNCTUATION_MISMATCH = "PUNCTUATION_MISMATCH"


class SeverityLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class VerificationType(str, Enum):
    TEXT_BASED = "TEXT_BASED"
    OCR_BASED = "OCR_BASED"


class StatusType(str, Enum):
    PASS = "PASS"
    WARNING = "WARNING"
    ERROR = "ERROR"


class CharacterDifference(BaseModel):
    diff_type: str = Field(..., description="'missing_char', 'extra_char', or 'changed_char'")
    char: str
    position: int
    orig_word: str
    extracted_word: str


class MismatchItem(BaseModel):
    id: str
    page: int
    line: int
    location: str
    orig_text: str
    extracted_text: str
    difference: str
    diff_type: DifferenceType
    severity: SeverityLevel
    confidence: Optional[float] = None
    char_diffs: List[CharacterDifference] = Field(default_factory=list)
    context: Optional[str] = None


class LineDiffItem(BaseModel):
    orig_line_num: Optional[int] = None
    ext_line_num: Optional[int] = None
    tag: str = Field(..., description="'equal', 'replace', 'delete', 'insert'")
    orig_line: str = ""
    extracted_line: str = ""
    diff_type: Optional[DifferenceType] = None
    mismatches: List[MismatchItem] = Field(default_factory=list)


class PageOriginalityResult(BaseModel):
    page: int
    orig_word_count: int
    extracted_word_count: int
    orig_char_count: int
    extracted_char_count: int
    accuracy: float
    status: StatusType
    verification_type: VerificationType
    preview_image_url: Optional[str] = None
    mismatches: List[MismatchItem] = Field(default_factory=list)
    orig_lines: List[str] = Field(default_factory=list)
    extracted_lines: List[str] = Field(default_factory=list)
    line_diffs: List[LineDiffItem] = Field(default_factory=list)


class OriginalityReport(BaseModel):
    report_id: str
    original_filename: str
    extracted_filename: str
    file_type: str
    timestamp: str
    overall_accuracy: float
    verification_status: StatusType
    job_id: Optional[str] = None
    preview_available: bool = True
    total_pages: int
    passed_pages: int
    warning_pages: int
    error_pages: int
    total_orig_words: int
    total_extracted_words: int
    missing_words: int
    extra_words: int
    changed_words: int
    character_errors: int
    number_mismatches: int
    punctuation_mismatches: int
    reading_order_issues: int
    pages: List[PageOriginalityResult] = Field(default_factory=list)
    summary_notes: List[str] = Field(default_factory=list)


class DocumentMetadata(BaseModel):
    filename: str
    file_type: str
    total_pages: Optional[int] = None
    total_sections: Optional[int] = None
    character_count: Optional[int] = None
    word_count: Optional[int] = None
    line_count: Optional[int] = None
