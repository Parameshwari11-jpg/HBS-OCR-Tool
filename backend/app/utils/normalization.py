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

def is_ui_artifact(text: Optional[str], bbox: Optional[List[float]] = None) -> bool:
    """
    Identifies UI control artifacts such as:
    - Dropdown combobox arrow buttons ('v', 'V', 'A', 'a', '^', '▼', '▾', '▽', etc. in small square boxes)
    - Window close buttons ('X', 'x' in corner/small square boxes)
    - Checkboxes / radio buttons / scrollbar arrows / isolated tiny punctuation noise
    Returns True if the item is a UI artifact and should NOT be treated as document text.
    """
    if not text:
        return True

    raw_t = text.strip()
    if not raw_t:
        return True

    w = 999.0
    h = 999.0
    ar = 1.0
    box_area = 999999.0

    if bbox and len(bbox) >= 4:
        w = float(bbox[2] - bbox[0])
        h = float(bbox[3] - bbox[1])
        ar = w / max(0.1, h)
        box_area = w * h

    # 1. Dropdown combo box arrow buttons (often detected as 'V', 'v', 'A', 'a', '^', '▼', '▾', '▽', 'u')
    # Typical dimensions in UI screenshots: 8x8 to 22x22 pixels, aspect ratio 0.6 - 1.6
    if raw_t in ('v', 'V', 'A', 'a', '^', '▼', '▾', '▽', '▲', '△', '▴', 'u', 'v.', 'V.', 'a.'):
        if (w <= 28 and h <= 28) or (box_area <= 650 and 0.6 <= ar <= 1.6):
            return True

    # Standalone 'v' or 'V' of modest size (height/width <= 32)
    # In standard English, standalone 'v' or 'V' does not exist as an isolated word in images
    if raw_t.lower() == 'v' and w <= 32 and h <= 32:
        return True

    # 2. Window close button 'X' or 'x' in a small square box
    if raw_t.lower() == 'x' and w <= 26 and h <= 26 and 0.7 <= ar <= 1.5:
        return True

    # 3. Tiny isolated noise glyphs (<= 18x18 pixels)
    if len(raw_t) == 1 and w <= 18 and h <= 18 and raw_t in '<>|_~-•·.':
        return True

    # 4. Checkbox / radio button / square box glyphs
    if raw_t in ('☐', '☑', '☒', '■', '□', '●', '○') and w <= 25 and h <= 25:
        return True

    return False

def clean_ocr_text(text: Optional[str]) -> str:
    """
    Cleans OCR artifacts and improves typography accuracy:
    - Fixes missing spaces after colons: "Title:Accounts" -> "Title: Accounts"
    - Strips combobox trailing button artifacts: "Upper rightd" -> "Upper right"
    - Strips combobox border dots: "Upper left." -> "Upper left"
    - Cleans duplicate whitespace
    """
    if not text:
        return ""

    t = text.strip()

    # Fix space after colon if missing: e.g. "Title:Accounts" -> "Title: Accounts"
    t = re.sub(r'([A-Za-z0-9]):([A-Za-z0-9])', r'\1: \2', t)

    # Clean combobox trailing dropdown artifacts: e.g. "Upper rightd" -> "Upper right"
    t = re.sub(r'\b(right|left|top|bottom|up|down|center|middle|none|yes|no|true|false)d\b', r'\1', t, flags=re.IGNORECASE)
    t = re.sub(r'\b(right|left|top|bottom)v\b', r'\1', t, flags=re.IGNORECASE)

    # Clean combobox trailing dot from border: e.g. "Date: Upper left." -> "Date: Upper left"
    t = re.sub(r'\b(Upper left|Upper right|Lower left|Lower right)\.', r'\1', t, flags=re.IGNORECASE)

    # Multiple spaces
    t = re.sub(r'\s+', ' ', t).strip()

    return t
