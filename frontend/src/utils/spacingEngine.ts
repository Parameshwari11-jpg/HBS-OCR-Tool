/**
 * Generic Token Boundary and Spacing Engine (TypeScript / Client-side).
 *
 * Implements the 4-Level decision pipeline for merging arbitrary text fragments:
 * - Level 1: Preserves existing whitespace.
 * - Level 2: Punctuation and typographical boundary rules.
 * - Level 3: Orthographic and pattern boundary rules.
 * - Level 4: Vocabulary, prefixes, and compound word analysis.
 *
 * Zero hardcoding. Fully document-agnostic.
 */

const PUNCT_NO_SPACE_BEFORE = new Set(['.', ',', ';', ':', '!', '?', ')', ']', '}', '%', "'", '"', '”', '’', '»']);
const PUNCT_NO_SPACE_AFTER = new Set(['(', '[', '{', '‘', '“', '«', '$', '#', '@']);
const MATH_OPERATORS = new Set(['+', '-', '−', '=', '*', '/', '<', '>', '≤', '≥', '≠', '±', '×', '÷']);

// Recognized productive English prefixes that form single words
const PREFIXES = new Set([
  'un', 're', 'in', 'im', 'dis', 'en', 'em', 'non', 'over', 'mis',
  'sub', 'pre', 'inter', 'fore', 'de', 'trans', 'super', 'semi',
  'anti', 'mid', 'under', 'micro', 'macro', 'auto', 'co'
]);

// Common English suffixes
const SUFFIXES = new Set([
  'ing', 'ed', 'tion', 'sion', 'able', 'ible', 'ment', 'ness',
  'less', 'ful', 'ity', 'ous', 'ship', 'hood', 'ward', 'wise'
]);

// Standard closed compound words
const CLOSED_COMPOUNDS = new Set([
  'everybody', 'everyone', 'everything', 'everywhere',
  'somebody', 'someone', 'something', 'somewhere',
  'anybody', 'anyone', 'anything', 'anywhere',
  'nobody', 'nothing', 'nowhere',
  'into', 'onto', 'upon', 'within', 'without', 'throughout',
  'cannot', 'maybe', 'already', 'almost', 'always',
  'meanwhile', 'furthermore', 'moreover', 'nevertheless',
  'lifestyle', 'database', 'filename', 'network', 'software',
  'hardware', 'keyboard', 'screenshot', 'setup', 'textbox',
  'toolbar', 'scrollbar', 'checkbox', 'dropdown', 'superscript'
]);

// Units and suffixes that attach directly after numbers without space
const UNITS_AND_SUFFIXES = new Set([
  'th', 'st', 'nd', 'rd',
  'px', 'pt', 'em', 'rem', 'vh', 'vw', '%',
  'mm', 'cm', 'km', 'kg', 'mg', 'ml', 'ms', 'hz', 'khz', 'mhz', 'ghz'
]);

export function shouldInsertSpace(
  leftRaw: string,
  rightRaw: string,
  coordGap?: number,
  fontSize?: number
): boolean {
  // Level 1: Preserve original whitespace
  if (leftRaw.endsWith(' ') || leftRaw.endsWith('\t') || leftRaw.endsWith('\n')) {
    return false;
  }
  if (rightRaw.startsWith(' ') || rightRaw.startsWith('\t') || rightRaw.startsWith('\n')) {
    return false;
  }

  const left = leftRaw.trim();
  const right = rightRaw.trim();

  if (!left || !right) {
    return false;
  }

  // Physical coordinate gap check if coordinates are available
  if (coordGap !== undefined && fontSize !== undefined && fontSize > 0) {
    if (coordGap >= 0.22 * fontSize) {
      return true;
    }
    if (coordGap < 0.05 * fontSize) {
      return false;
    }
  }

  // Level 2: Punctuation and Typography Rules
  const lastChar = left[left.length - 1];
  const firstChar = right[0];

  // Contraction / possessive suffix e.g. "word" + "'s", "don" + "'t"
  if (right.startsWith("'") || right.startsWith("’")) {
    if (right.length <= 3 && /^[a-zA-Z]+$/.test(right.slice(1))) {
      return false;
    }
  }

  // Hyphens e.g. "semi-" + "annual"
  if ('-–—'.includes(lastChar) || '-–—'.includes(firstChar)) {
    return false;
  }

  // Left ends with opening bracket/symbol e.g. "(" + "word"
  if (PUNCT_NO_SPACE_AFTER.has(lastChar)) {
    return false;
  }

  // Right starts with closing bracket/punctuation e.g. "word" + ","
  if (PUNCT_NO_SPACE_BEFORE.has(firstChar)) {
    return false;
  }

  // Left ends with sentence-ending or clause punctuation e.g. "word." + "Next"
  if ('.,;:!?»)]}'.includes(lastChar)) {
    // Decimal point in numbers: "3." + "14"
    if (lastChar === '.' && /^\d+$/.test(left.slice(0, -1)) && /^\d+$/.test(right)) {
      return false;
    }
    // Acronyms e.g. "U." + "S." + "A."
    if (lastChar === '.' && left.length <= 2 && right.length <= 2 && /^[A-Z]\.?$/.test(left) && /^[A-Z]\.?$/.test(right)) {
      return false;
    }
    return true;
  }

  // Math operators
  if (MATH_OPERATORS.has(lastChar) || MATH_OPERATORS.has(firstChar)) {
    return true;
  }

  // Extract boundary word/token from each fragment
  const leftTokens = left.match(/[a-zA-Z0-9]+/g);
  const rightTokens = right.match(/[a-zA-Z0-9]+/g);

  const bLeft = leftTokens ? leftTokens[leftTokens.length - 1] : left;
  const bRight = rightTokens ? rightTokens[0] : right;

  // Level 3: Orthographic & Character Class Transitions
  const isLeftAlpha = /^[a-zA-Z]+$/.test(bLeft);
  const isRightAlpha = /^[a-zA-Z]+$/.test(bRight);
  const isLeftDigits = /^\d+$/.test(bLeft);
  const isRightDigits = /^\d+$/.test(bRight);

  // Letter + Digit e.g. "Chapter" + "5"
  if (isLeftAlpha && isRightDigits) {
    return true;
  }

  // Digit + Letter / Unit
  if (isLeftDigits && isRightAlpha) {
    if (UNITS_AND_SUFFIXES.has(bRight.toLowerCase())) {
      return false;
    }
    return true;
  }

  // Capitalization patterns:
  // Case 1: TitleCase / Capitalized + TitleCase / Capitalized: "Contributing" + "Writers" -> Space
  const isLeftTitle = /^[A-Z][a-z]+$/.test(bLeft);
  const isRightTitle = /^[A-Z][a-z]+$/.test(bRight);
  if (isLeftTitle && isRightTitle) {
    return true;
  }

  // Case 2: ALL CAPS + ALL CAPS
  const isLeftUpper = /^[A-Z]{2,}$/.test(bLeft);
  const isRightUpper = /^[A-Z]{2,}$/.test(bRight);
  if (isLeftUpper && isRightUpper) {
    return true;
  }

  // Case 3: lowercase + Capital (camelCase / word boundary)
  if (/^[a-z]+$/.test(bLeft) && /^[A-Z][a-z]*$/.test(bRight)) {
    return true;
  }

  // Level 4: Vocabulary and Compound Word Analysis
  if (isLeftAlpha && isRightAlpha) {
    const leftClean = bLeft.toLowerCase();
    const rightClean = bRight.toLowerCase();
    const combined = leftClean + rightClean;

    // Prefixes
    if (PREFIXES.has(leftClean)) {
      return false;
    }

    // Suffixes
    if (SUFFIXES.has(rightClean)) {
      return false;
    }

    // Known closed compounds
    if (CLOSED_COMPOUNDS.has(combined)) {
      return false;
    }

    // Default for two alphanumeric words: insert space
    return true;
  }

  // Fallback: two alphanumeric tokens
  if (/^[a-zA-Z0-9]+$/.test(bLeft) && /^[a-zA-Z0-9]+$/.test(bRight)) {
    return true;
  }

  return false;
}

/**
 * Merges an arbitrary list of fragments T1 + T2 + ... + Tn
 * evaluating every boundary independently.
 */
export function mergeTokens(
  fragments: string[],
  coordGaps?: (number | undefined)[],
  fontSizes?: (number | undefined)[]
): string {
  if (!fragments || fragments.length === 0) return '';
  if (fragments.length === 1) return fragments[0];

  const result: string[] = [fragments[0]];

  for (let i = 1; i < fragments.length; i++) {
    const prev = result[result.length - 1];
    const curr = fragments[i];
    const gap = coordGaps?.[i - 1];
    const fs = fontSizes?.[i - 1];

    if (shouldInsertSpace(prev, curr, gap, fs)) {
      result.push(' ');
    }
    result.push(curr);
  }

  return result.join('');
}
