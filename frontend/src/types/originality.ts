export type DifferenceType =
  | 'EXACT_MATCH'
  | 'NUMBER_MISMATCH'
  | 'WORD_MISMATCH'
  | 'CHARACTER_MISMATCH'
  | 'MISSING_TEXT'
  | 'EXTRA_TEXT'
  | 'READING_ORDER'
  | 'PUNCTUATION_MISMATCH';

export type SeverityLevel = 'HIGH' | 'MEDIUM' | 'LOW';

export type VerificationType = 'TEXT_BASED' | 'OCR_BASED';

export type StatusType = 'PASS' | 'WARNING' | 'ERROR';

export interface CharacterDifference {
  diff_type: string;
  char: string;
  position: number;
  orig_word: string;
  extracted_word: string;
}

export interface MismatchItem {
  id: string;
  page: number;
  line: number;
  location: string;
  orig_text: string;
  extracted_text: string;
  difference: string;
  diff_type: DifferenceType;
  severity: SeverityLevel;
  confidence?: number;
  char_diffs: CharacterDifference[];
  context?: string;
}

export interface LineDiffItem {
  orig_line_num?: number;
  ext_line_num?: number;
  tag: 'equal' | 'replace' | 'delete' | 'insert';
  orig_line: string;
  extracted_line: string;
  diff_type?: DifferenceType;
  mismatches: MismatchItem[];
}

export interface PageOriginalityResult {
  page: number;
  orig_word_count: number;
  extracted_word_count: number;
  orig_char_count: number;
  extracted_char_count: number;
  accuracy: number;
  status: StatusType;
  verification_type: VerificationType;
  preview_image_url?: string;
  mismatches: MismatchItem[];
  orig_lines: string[];
  extracted_lines: string[];
  line_diffs: LineDiffItem[];
}

export interface OriginalityReport {
  report_id: string;
  original_filename: string;
  extracted_filename: string;
  file_type: string;
  timestamp: string;
  overall_accuracy: number;
  verification_status: StatusType;
  job_id?: string;
  preview_available?: boolean;
  total_pages: number;
  passed_pages: number;
  warning_pages: number;
  error_pages: number;
  total_orig_words: number;
  total_extracted_words: number;
  missing_words: number;
  extra_words: number;
  changed_words: number;
  character_errors: number;
  number_mismatches: number;
  punctuation_mismatches: number;
  reading_order_issues: number;
  pages: PageOriginalityResult[];
  summary_notes: string[];
}

export interface DocumentMetadata {
  filename: string;
  file_type: string;
  total_pages?: number;
  total_sections?: number;
  character_count?: number;
  word_count?: number;
  line_count?: number;
}
