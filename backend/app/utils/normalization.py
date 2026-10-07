import re
import unicodedata
from typing import List, Optional

def normalize_text(text: str) -> str:
    if not text:
        return ""
    # NFKC normalization
    text = unicodedata.normalize('NFKC', text)
    # Convert to lowercase
    text = text.lower()
    # Remove extra whitespaces/newlines
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def calculate_text_similarity(str1: str, str2: str) -> float:
    n1 = normalize_text(str1)
    n2 = normalize_text(str2)
    
    if not n1 or not n2:
        return 0.0
    if n1 == n2:
        return 1.0
        
    # Sequence Matcher / Jaccard Word N-gram similarity
    words1 = set(n1.split())
    words2 = set(n2.split())
    
    if not words1 or not words2:
        return 0.0
        
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    jaccard = len(intersection) / len(union)
    
    # Substring check only if length ratio is high (e.g. > 0.65) and min length > 10
    # Prevents short single words like 'finish' from claiming 0.85 similarity with whole sentences
    min_len = min(len(n1), len(n2))
    max_len = max(len(n1), len(n2))
    ratio = min_len / max(1, max_len)

    if (n1 in n2 or n2 in n1) and min_len > 10 and ratio > 0.65:
        jaccard = max(jaccard, 0.85)
        
    return jaccard

WINDOW_CTRL_PATTERN = re.compile(
    r'^[\-_—–\s]*([xX✕✖×]|(?:[口□◻oO0\[\]\(\)\-_—–\s]+[xX✕✖×]))[\-_—–\s]*$'
)

DROPDOWN_ARROW_PATTERN = re.compile(
    r'^[|\[\(]?\s*([vV▼▾▽▲△▴u\^Aa]|v\.|V\.|a\.|A\.)\s*[|\]\)]?$'
)

CHECKBOX_GLYPH_PATTERN = re.compile(
    r'^(?:\[\s*\]|\(\s*\)|[☐☑☒■□●○✓✔√•·\-_—–])$'
)

def is_ui_artifact(
    text: Optional[str],
    bbox: Optional[List[float]] = None,
    confidence: Optional[float] = None
) -> bool:
    """
    Identifies UI control artifacts such as:
    - Dropdown combobox arrow buttons ('v', 'V', '^', '▼', '▾', '▽', etc.)
    - Drop-up / scrollbar up-arrow buttons ('A', 'a', '^', '▲', '△', etc. in small button boxes)
    - Window caption/close buttons ('_ x', '_x', 'X', 'x', '- x', '— x', etc.)
    - Standalone checkboxes, radio buttons, ticks, and bullet noise
    - Low-confidence OCR noise
    Returns True if the item is a UI artifact and should NOT be treated as document text.
    """
    if not text:
        return True

    raw_t = text.strip()
    if not raw_t:
        return True

    conf_norm: Optional[float] = None
    if confidence is not None:
        try:
            c = float(confidence)
            conf_norm = c / 100.0 if c > 1.0 else c
        except (ValueError, TypeError):
            pass

    w = 999.0
    h = 999.0
    ar = 1.0
    box_area = 999999.0

    if bbox and len(bbox) >= 4:
        w = float(bbox[2] - bbox[0])
        h = float(bbox[3] - bbox[1])
        ar = w / max(0.1, h)
        box_area = w * h

    # 1. Very low confidence noise across the board (< 0.40)
    if conf_norm is not None and conf_norm < 0.40:
        return True

    # 2. Window control buttons: minimize, maximize, close
    # Matches '_ x', '_x', '_ X', '- x', '— x', '_ [] x', standalone 'x'/'X'
    if WINDOW_CTRL_PATTERN.match(raw_t):
        # Multi-char caption button like '_ x', '- x' is always a window UI control
        if len(raw_t) > 1:
            return True
        # Standalone 'x', 'X', '×': in image OCR, standalone single letter X is close button/checkbox
        if raw_t.lower() in ('x', '×', '✕', '✖'):
            if (w <= 60 and h <= 60) or (0.5 <= ar <= 1.8 and box_area <= 3600):
                return True
            if conf_norm is not None and conf_norm < 0.85:
                return True

    # 3. Dropdown combobox and drop-up/scroll-up arrow buttons ('v', 'V', 'A', 'a', '^', '▼', etc.)
    if DROPDOWN_ARROW_PATTERN.match(raw_t):
        # For 'A' or 'a' (drop-up arrow / scroll-up / spin-up button in UI forms):
        # Wisely check that it is a small button icon (e.g. 8x10 px in scrollbars / spin controls)
        if raw_t in ('A', 'a', 'A.', 'a.'):
            if (w <= 28 and h <= 28) and (0.5 <= ar <= 1.6) and box_area <= 650:
                return True
        else:
            # For 'v', 'V', '▼', '^', etc. (dropdown arrows)
            if (w <= 60 and h <= 60) or (box_area <= 3600 and 0.5 <= ar <= 2.0):
                return True
            if raw_t.lower() in ('v', 'v.'):
                # In English text, standalone 'v' or 'V' is never an isolated word
                return True

    # 4. Checkbox / radio button / bullet standalone glyphs
    if CHECKBOX_GLYPH_PATTERN.match(raw_t):
        return True

    # Standalone empty checkbox / radio button glyph:
    # Only treat 'o' or 'O' (or low-confidence '0') in a square box as checkbox noise
    if raw_t in ('o', 'O') and (w <= 36 and h <= 36 and 0.65 <= ar <= 1.5):
        return True
    if raw_t == '0' and (w <= 36 and h <= 36 and 0.65 <= ar <= 1.5):
        # A legitimate numeric '0' on graph axes or tables usually has confidence >= 0.60
        # Only discard if extremely low confidence (< 0.50)
        if conf_norm is not None and conf_norm < 0.50:
            return True

    # Standalone tick / cursor / bar noise:
    # '|' or non-digit line noise
    if raw_t in ('|', 'l') and (w <= 30 and h <= 30):
        if ar >= 0.55 or (conf_norm is not None and conf_norm < 0.85):
            return True
    elif raw_t == '1' and (w <= 30 and h <= 30):
        # Genuine digit '1' in graph axes / tables: only discard if very low confidence (< 0.50)
        if conf_norm is not None and conf_norm < 0.50:
            return True

    # 5. Isolated punctuation / line noise (<= 2 chars)
    if len(raw_t) <= 2 and not any(c.isalnum() for c in raw_t):
        if (w <= 25 and h <= 25) or (conf_norm is not None and conf_norm < 0.80):
            return True

    # 6. Standalone single non-word letter or noise glyph (e.g. 'C', 'c', 'v', 'x', 'o', 'e')
    # Valid standalone single-letter words in English are 'a', 'A', 'I', but even these should not
    # appear as isolated OCR results from embedded images unless they are toolbar labels or large icons.
    # Any single letter that is NOT a digit, with low confidence or in a small button bbox is an artifact.
    if len(raw_t) == 1 and not raw_t.isdigit():
        if raw_t not in ('a', 'A', 'I'):
            # Non-word single letter: confident threshold is 0.90
            if conf_norm is not None and conf_norm < 0.90:
                return True
            if w <= 65 and h <= 65:
                return True
        else:
            # 'a', 'A', 'I' — only allow if confidence >= 0.75 (very low conf = icon/glyph noise)
            if conf_norm is not None and conf_norm < 0.75:
                return True


    # 7. Standalone short glyph/digit (<= 2 chars) in a small button icon box (w <= 35, h <= 35)
    # e.g., window title bar pin/minimize/collapse/close icons misdetected as '4' or '11'
    # IMPORTANT: Do NOT discard valid numeric coordinates, axis markers, scores or values (e.g. '0', '1', '2', '83', '76', '96')
    if len(raw_t) <= 2 and (w <= 35 and h <= 35 and box_area <= 1200):
        # If it's a pure digit/number, only treat as artifact if confidence is very low (< 0.40)
        if raw_t.isdigit():
            if conf_norm is not None and conf_norm < 0.40:
                return True
        else:
            return True

    return False

def clean_leading_ocr_checkbox(text: str) -> str:
    """
    Cleans OCR checkbox and bullet misrecognitions at the start of lines/words:
    - '0Show shading' -> 'Show shading'
    - '1CHECK' -> 'CHECK'
    - '0 Show shading' -> 'Show shading'
    - 'SShow shading' -> 'Show shading'
    - 'vCHECK' -> 'CHECK'
    - 'xAMOUNT' -> 'AMOUNT'
    - Preserves ordinals: '1st', '2nd', '3rd', '4th'
    - Preserves technical codes: '3D', '4K', '2FA', '5G', '1080p', '64bit'
    - Preserves legitimate numbered lists: '8. Create...', '1. Introduction', '1) Step', '5.3 Print'
    - Preserves pure numbers: '220', '280', '1/4/2019', '34.179.48'
    """
    if not text:
        return ""

    protected_tech = r'(?:st|nd|rd|th|d|D|k|K|g|G|fa|FA|bit|BIT|p|P)\b'
    # 1. Leading digit(s) attached directly to an alphabetic word: '0Show' -> 'Show', '1CHECK' -> 'CHECK'
    text = re.sub(rf'^[0-9]+(?!(?:{protected_tech}))([A-Za-z_][A-Za-z0-9_]*)', r'\1', text)

    # 2. Leading '0 ' (zero followed by space and letter): '0 Show' -> 'Show'
    text = re.sub(r'^0\s+([A-Za-z])', r'\1', text)

    # 3. Checkbox square misrecognized as 'S' or 'O' before 'Show': 'SShow' -> 'Show', 'OShow' -> 'Show'
    text = re.sub(r'^[SsOo]Show\b', 'Show', text)

    # 4. Leading checkbox glyphs: '[ ]', '[]', '☐', etc.
    text = re.sub(r'^(?:\[\s*\]|[\[\(][xXvV01\s][\]\)]|[☐☑☒■□●○✓✔√•·])\s*', '', text)

    # 5. Checkbox tick/cross/square attached to all-caps word: 'vCHECK' -> 'CHECK', 'xAMOUNT' -> 'AMOUNT'
    text = re.sub(r'^[vxoVXO_]([A-Z]{3,}\b)', r'\1', text)

    # 6. OCR bullet / arrow artifacts at line start:
    # e.g., '> Napoleon Bonaparte' -> 'Napoleon Bonaparte'
    # e.g., '. exchange names' -> 'exchange names'
    # e.g., ': greet someone' -> 'greet someone'
    # e.g., '. L\'Europe' -> 'L\'Europe'
    # Preserves legitimate numbered lists: '1. Introduction', '1.2 Heading'
    text = re.sub(r'^[>•·~–—]\s*', '', text)
    text = re.sub(r'^[.:]\s+([A-Za-zÀ-ÿ])', r'\1', text)

    # 7. Stray circular icon or bullet attached to start of capitalized word: 'OQue' -> 'Que'
    text = re.sub(r'^[Oo]([A-Z][a-z]{2,})', r'\1', text)

    # 8. Trailing duplicate or misplaced dots after punctuation: e.g. 'World!.' -> 'World!', 'shell..' -> 'shell.', 'photo?.' -> 'photo?'
    # Only replaces exactly two dots (preserves legitimate ellipsis '...' and '....')
    text = re.sub(r'([!?])\s*\.+$', r'\1', text)
    text = re.sub(r'(?<!\.)\.\.(?!\.)$', '.', text)

    return text.strip()

def clean_ocr_text(text: Optional[str]) -> str:
    """
    Cleans OCR artifacts and improves typography accuracy:
    - Cleans leading checkbox artifacts (0Show -> Show, 1CHECK -> CHECK, SShow -> Show)
    - Fixes missing spaces after colons: "Title:Accounts" -> "Title: Accounts"
    - Strips combobox trailing button artifacts: "Upper rightd" -> "Upper right"
    - Strips combobox border dots: "Upper left." -> "Upper left"
    - Cleans duplicate whitespace while preserving legitimate document text and numbers
    """
    if not text:
        return ""

    lines = []
    for line in text.splitlines():
        line_clean = clean_leading_ocr_checkbox(line)
        if not line_clean:
            continue
        # Fix space after colon if missing: e.g. "Title:Accounts" -> "Title: Accounts"
        line_clean = re.sub(r'([A-Za-z0-9]):([A-Za-z0-9])', r'\1: \2', line_clean)
        # Clean combobox trailing dropdown artifacts: e.g. "Upper rightd" -> "Upper right"
        line_clean = re.sub(r'\b(right|left|top|bottom|up|down|center|middle|none|yes|no|true|false)d\b', r'\1', line_clean, flags=re.IGNORECASE)
        line_clean = re.sub(r'\b(right|left|top|bottom)v\b', r'\1', line_clean, flags=re.IGNORECASE)
        # Clean combobox trailing dot from border: e.g. "Date: Upper left." -> "Date: Upper left"
        line_clean = re.sub(r'\b(Upper left|Upper right|Lower left|Lower right)\.', r'\1', line_clean, flags=re.IGNORECASE)
        # Multiple spaces
        line_clean = re.sub(r'\s+', ' ', line_clean).strip()
        if line_clean:
            lines.append(line_clean)

    return "\n".join(lines)



