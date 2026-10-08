/**
 * Centralized language configuration for the OCR engine.
 *
 * To add a new language:
 * 1. Add an entry to SUPPORTED_LANGUAGES with its display label and OCR code.
 * 2. That's it — the dropdown, API call, and backend mapping all pick it up automatically.
 *
 * PaddleOCR language codes reference:
 *   https://paddlepaddle.github.io/PaddleOCR/latest/en/ppocr/blog/multi_languages.html
 */

export interface LanguageOption {
  /** ISO-style display code shown in the UI (informational) */
  code: string;
  /** Human-readable label shown in the dropdown */
  label: string;
  /** Language code passed to PaddleOCR (e.g. 'en', 'fr', 'es') */
  ocrCode: string;
}

export const SUPPORTED_LANGUAGES: LanguageOption[] = [
  { code: 'en', label: 'English', ocrCode: 'en' },
  { code: 'fr', label: 'French',  ocrCode: 'fr' },
  { code: 'es', label: 'Spanish', ocrCode: 'es' },
  // --- Add more languages below ---
  // { code: 'de', label: 'German',  ocrCode: 'german' },
  // { code: 'it', label: 'Italian', ocrCode: 'it' },
  // { code: 'hi', label: 'Hindi',   ocrCode: 'hi' },
  // { code: 'ta', label: 'Tamil',   ocrCode: 'ta' },
];

/** The OCR code for a given display code, or 'en' if not found. */
export function getOcrCode(code: string): string {
  return SUPPORTED_LANGUAGES.find((l) => l.code === code)?.ocrCode ?? 'en';
}
