import re
import statistics
from typing import Optional, List, Dict, Any
from app.models.extraction_models import FontInfo, TaggingSummary, ExtractedElement

class TagClassifier:
    """
    Semantic classifier and parameter generator for document elements.
    Handles both TAGGED and UNTAGGED PDF and Word (.docx) documents.
    Generates exact content_type, tag, is_tagged, tag_source, and rich parameters.
    """

    BULLET_REGEX = re.compile(
        r'^([•\-\*\u2022\u25E6\u25AA\u25CF\u2013\u2014]|\d+(\.\d+)*[\.\)]|\([0-9a-zA-Z]+\)|[a-zA-Z][\.\)])\s+'
    )
    CAPTION_REGEX = re.compile(
        r'^(Figure|Fig\.|Table|Tab\.|Diagram|Chart|Exhibit|Illustration)\s+\d+[:\.]?',
        re.IGNORECASE
    )
    SECTION_HEADING_REGEX = re.compile(
        r'^(Chapter|Section|Part|Unit|Module)\s+(\d+|[IVXLCDM]+)[:\.\s]?',
        re.IGNORECASE
    )
    NUMBERED_HEADING_REGEX = re.compile(
        r'^\d+(\.\d+){1,3}\s+[A-Z]'
    )
    CODE_FONTS = {
        'courier', 'couriernew', 'consolas', 'menlo', 'monaco', 'sourcecodepro',
        'dejavusansmono', 'lucidaconsole', 'inconsolata', 'firamono', 'robotomono'
    }

    @staticmethod
    def is_math_or_formula(text: Optional[str]) -> bool:
        if not text:
            return False
        t = text.strip()
        # LaTeX / MathType commands
        if any(tok in t.lower() for tok in ['\\frac', '\\sqrt', '\\sum', '\\int', '\\prod', 'mathtype', 'omath']):
            return True

        # Prose sentences with multiple alphabetic words should be paragraphs, not formula blocks
        words = t.split()
        alpha_words = [w for w in words if re.match(r'^[A-Za-z]{3,}$', w)]
        if len(alpha_words) >= 5:
            return False

        # Math operator Unicode symbols
        math_chars = set('∀∁∂∃∄∅∆∇∈∉∊∋∌∍∎∏∐∑−∓∔∕∖∗∘∙√∛∜∝∞∟∠∡∢∣∤∥∦∧∨∩∪∫∬∭∮∯∰∱∲∳∴∵∶∷∸∹∺∻∼∽∾∿≀≁≂≃≄≅≆≇≈≉≊≋≌≍≎≏≐≑≒≓≔≕≖≗≘≙≚≜≝≞≟≠≡≢≣≤≥≦≧≨≩≪≫≬≭≮≯≰≱≲≳≴≵≶≷≸≹≺≻≼≽≾≿⊀⊁⊂⊃⊄⊅⊆⊇⊈⊉⊊⊋⊌⊍⊎⊏⊐⊑⊒⊓⊔⊕⊖⊗⊘⊙⊚⊛⊜⊝⊞⊟⊠⊡⊢⊣⊤⊥⊦⊧⊨⊩⊪⊫⊬⊭⊮⊯⊰⊱⊲⊳⊴⊵⊶⊷⊸⊹⊺⊻⊼⊽⊾⊿⋅⋆✕✖✚±×÷')
        if any(c in math_chars for c in t):
            return True
        # Equation pattern like a = b + c or f(x) = y
        if '=' in t and not any(tag in t for tag in ['<', '>', '==', '!=', 'http', 'href', 'xmlns']):
            if re.search(r'\b[a-zA-Z_0-9]\s*=\s*[-0-9a-zA-Z\+\*\/\(\)]', t):
                return True
        # Algebraic fraction or arithmetic operation e.g. 7/10 - 2/10 or 3a/a - 4
        if re.search(r'\b[a-zA-Z0-9]+/[a-zA-Z0-9]+', t) and re.search(r'[-+*/^=]', t):
            return True
        return False

    @classmethod
    def compute_median_font_size(cls, font_sizes: List[float], fallback: float = 11.0) -> float:
        valid_sizes = [s for s in font_sizes if 5.0 <= s <= 40.0]
        if not valid_sizes:
            return fallback
        try:
            return float(statistics.median(valid_sizes))
        except Exception:
            return fallback

    @classmethod
    def classify_element(
        cls,
        text: Optional[str] = None,
        bbox: Optional[List[float]] = None,
        font_info: Optional[FontInfo] = None,
        page_width: float = 612.0,
        page_height: float = 792.0,
        median_body_size: float = 11.0,
        explicit_style: Optional[str] = None,
        has_xml_num_pr: bool = False,
        is_table: bool = False,
        is_image: bool = False,
        is_formula: bool = False,
        doc_is_tagged: bool = False,
        source: str = "native",
        table_rows: Optional[List[List[str]]] = None,
        table_headers: Optional[List[str]] = None,
        image_meta: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Classifies an element and builds its content_type, tag, is_tagged, tag_source, and parameters.
        """
        clean_text = (text or "").strip()
        word_count = len(clean_text.split()) if clean_text else 0
        char_count = len(clean_text)
        line_count = len(clean_text.splitlines()) if clean_text else 0

        font_name = getattr(font_info, "name", None) if font_info else None
        font_size = float(getattr(font_info, "size", 0) or 0) if font_info else 0.0
        is_bold = bool(getattr(font_info, "bold", False)) if font_info else False
        is_italic = bool(getattr(font_info, "italic", False)) if font_info else False
        font_color = getattr(font_info, "color", None) if font_info else None

        effective_size = font_size if font_size > 0 else median_body_size

        # 1. TABLE Content Type
        if is_table or (table_rows is not None and len(table_rows) > 0):
            rows = table_rows or []
            headers = table_headers or []
            row_count = len(rows)
            col_count = len(headers) if headers else (len(rows[0]) if rows else 0)
            total_cells = (row_count * col_count) + (len(headers) if headers and not rows else 0)

            is_tagged_elem = True if (explicit_style or doc_is_tagged or source in ("docx", "docx_xml")) else False
            tag_src = "docx_style" if source == "docx" else ("pdf_struct_tree" if doc_is_tagged else "layout_inference")

            return {
                "content_type": "table",
                "tag": "Table",
                "is_tagged": is_tagged_elem,
                "tag_source": tag_src,
                "parameters": {
                    "content_type": "table",
                    "tag": "Table",
                    "is_tagged": is_tagged_elem,
                    "tag_source": tag_src,
                    "row_count": row_count,
                    "column_count": col_count,
                    "has_header": bool(headers),
                    "headers": headers,
                    "total_cells": total_cells,
                    "bbox": bbox
                }
            }

        # 2. IMAGE / FIGURE Content Type
        if is_image:
            meta = image_meta or {}
            w = meta.get("width") or (int(bbox[2] - bbox[0]) if bbox and len(bbox) == 4 else 0)
            h = meta.get("height") or (int(bbox[3] - bbox[1]) if bbox and len(bbox) == 4 else 0)
            aspect_ratio = round(w / max(1, h), 2) if w and h else 1.0
            tag_src = "docx_xml" if "docx" in source else "native"

            return {
                "content_type": "image",
                "tag": "Image",
                "is_tagged": True,
                "tag_source": tag_src,
                "parameters": {
                    "content_type": "image",
                    "tag": "Image",
                    "is_tagged": True,
                    "tag_source": tag_src,
                    "image_id": meta.get("image_id"),
                    "image_path": meta.get("image_path"),
                    "width": w,
                    "height": h,
                    "aspect_ratio": aspect_ratio,
                    "format": meta.get("format", "png"),
                    "bbox": bbox
                }
            }

        # 3. FORMULA / EQUATION Content Type
        if is_formula or cls.is_math_or_formula(clean_text):
            is_mtef = "mathtype" in (source or "").lower() or (image_meta or {}).get("subtype") == "mathtype_ole"
            formula_type = "mathtype_mtef" if is_mtef else ("omml" if "omml" in source else "latex_or_ascii")
            is_tagged_elem = True if (source in ("mathtype", "docx_xml") or doc_is_tagged) else False
            tag_src = "docx_xml" if source in ("mathtype", "docx_xml") else ("pdf_struct_tree" if doc_is_tagged else "layout_inference")

            return {
                "content_type": "formula",
                "tag": "Formula",
                "is_tagged": is_tagged_elem,
                "tag_source": tag_src,
                "parameters": {
                    "content_type": "formula",
                    "tag": "Formula",
                    "is_tagged": is_tagged_elem,
                    "tag_source": tag_src,
                    "formula_type": formula_type,
                    "is_inline": line_count <= 1 and word_count <= 10,
                    "has_math_operators": True,
                    "character_count": char_count,
                    "bbox": bbox
                }
            }

        # 4. EXPLICIT WORD STYLES (Tagged Word Documents)
        if explicit_style:
            norm_style = explicit_style.strip().lower()
            if "title" in norm_style:
                return {
                    "content_type": "title",
                    "tag": "Title",
                    "is_tagged": True,
                    "tag_source": "docx_style",
                    "parameters": {
                        "content_type": "title",
                        "tag": "Title",
                        "is_tagged": True,
                        "tag_source": "docx_style",
                        "level": 0,
                        "style_name": explicit_style,
                        "font_size": effective_size,
                        "is_bold": is_bold,
                        "word_count": word_count,
                        "character_count": char_count,
                        "bbox": bbox
                    }
                }
            for lvl in range(1, 7):
                if f"heading {lvl}" in norm_style or f"h{lvl}" == norm_style:
                    ctype = f"heading_{lvl}" if lvl <= 3 else "heading"
                    return {
                        "content_type": ctype,
                        "tag": f"H{lvl}",
                        "is_tagged": True,
                        "tag_source": "docx_style",
                        "parameters": {
                            "content_type": ctype,
                            "tag": f"H{lvl}",
                            "is_tagged": True,
                            "tag_source": "docx_style",
                            "level": lvl,
                            "style_name": explicit_style,
                            "font_size": effective_size,
                            "is_bold": is_bold,
                            "word_count": word_count,
                            "character_count": char_count,
                            "bbox": bbox
                        }
                    }
            if "bullet" in norm_style or "list" in norm_style:
                ltype = "bullet" if "bullet" in norm_style else "numbered"
                return {
                    "content_type": "list_item",
                    "tag": "LI",
                    "is_tagged": True,
                    "tag_source": "docx_style",
                    "parameters": {
                        "content_type": "list_item",
                        "tag": "LI",
                        "is_tagged": True,
                        "tag_source": "docx_style",
                        "list_type": ltype,
                        "style_name": explicit_style,
                        "word_count": word_count,
                        "character_count": char_count,
                        "bbox": bbox
                    }
                }
            if "caption" in norm_style:
                return {
                    "content_type": "caption",
                    "tag": "Caption",
                    "is_tagged": True,
                    "tag_source": "docx_style",
                    "parameters": {
                        "content_type": "caption",
                        "tag": "Caption",
                        "is_tagged": True,
                        "tag_source": "docx_style",
                        "style_name": explicit_style,
                        "word_count": word_count,
                        "character_count": char_count,
                        "bbox": bbox
                    }
                }
            if "header" in norm_style:
                return {
                    "content_type": "header",
                    "tag": "Header",
                    "is_tagged": True,
                    "tag_source": "docx_style",
                    "parameters": {
                        "content_type": "header",
                        "tag": "Header",
                        "is_tagged": True,
                        "tag_source": "docx_style",
                        "position": "top",
                        "bbox": bbox
                    }
                }
            if "footer" in norm_style:
                return {
                    "content_type": "footer",
                    "tag": "Footer",
                    "is_tagged": True,
                    "tag_source": "docx_style",
                    "parameters": {
                        "content_type": "footer",
                        "tag": "Footer",
                        "is_tagged": True,
                        "tag_source": "docx_style",
                        "position": "bottom",
                        "bbox": bbox
                    }
                }

        # 5. WORD XML LIST ITEM (w:numPr)
        if has_xml_num_pr:
            return {
                "content_type": "list_item",
                "tag": "LI",
                "is_tagged": True,
                "tag_source": "docx_xml",
                "parameters": {
                    "content_type": "list_item",
                    "tag": "LI",
                    "is_tagged": True,
                    "tag_source": "docx_xml",
                    "list_type": "numbered",
                    "word_count": word_count,
                    "character_count": char_count,
                    "bbox": bbox
                }
            }

        # 6. UNTAGGED CONTENT CLASSIFICATION
        is_short_text = word_count <= 25 and line_count <= 3 and not clean_text.rstrip().endswith('.')

        # A. Position-based Header / Footer
        if bbox and len(bbox) == 4 and page_height > 0:
            y0, y1 = bbox[1], bbox[3]
            # Header: Top margin
            if y0 <= page_height * 0.075 and is_short_text:
                return {
                    "content_type": "header",
                    "tag": "Header",
                    "is_tagged": False,
                    "tag_source": "layout_inference",
                    "parameters": {
                        "content_type": "header",
                        "tag": "Header",
                        "is_tagged": False,
                        "tag_source": "layout_inference",
                        "position": "top",
                        "page_top_distance": round(y0, 1),
                        "word_count": word_count,
                        "bbox": bbox
                    }
                }
            # Footer: Bottom margin
            if y1 >= page_height * 0.925 and is_short_text:
                is_pg_num = bool(re.match(r'^\s*(\d+|page\s+\d+(\s+of\s+\d+)?|\b[ivxlcdm]+\b)\s*$', clean_text, re.I))
                return {
                    "content_type": "footer",
                    "tag": "Footer",
                    "is_tagged": False,
                    "tag_source": "layout_inference",
                    "parameters": {
                        "content_type": "footer",
                        "tag": "Footer",
                        "is_tagged": False,
                        "tag_source": "layout_inference",
                        "position": "bottom",
                        "is_page_number": is_pg_num,
                        "page_bottom_distance": round(page_height - y1, 1),
                        "word_count": word_count,
                        "bbox": bbox
                    }
                }

        # B. Caption Pattern: "Figure 1: ...", "Table 2. ..."
        if match := cls.CAPTION_REGEX.match(clean_text):
            return {
                "content_type": "caption",
                "tag": "Caption",
                "is_tagged": False,
                "tag_source": "layout_inference",
                "parameters": {
                    "content_type": "caption",
                    "tag": "Caption",
                    "is_tagged": False,
                    "tag_source": "layout_inference",
                    "caption_prefix": match.group(0).strip(),
                    "word_count": word_count,
                    "character_count": char_count,
                    "bbox": bbox
                }
            }

        # C. Bullet or Numbered List Item
        if match := cls.BULLET_REGEX.match(clean_text):
            marker = match.group(1)
            is_num = bool(re.search(r'\d|[a-zA-Z]', marker))
            clean_item_text = clean_text[match.end():].strip()
            return {
                "content_type": "list_item",
                "tag": "LI",
                "is_tagged": False,
                "tag_source": "layout_inference",
                "parameters": {
                    "content_type": "list_item",
                    "tag": "LI",
                    "is_tagged": False,
                    "tag_source": "layout_inference",
                    "list_type": "numbered" if is_num else "bullet",
                    "marker": marker,
                    "clean_text": clean_item_text,
                    "word_count": word_count,
                    "character_count": char_count,
                    "bbox": bbox
                }
            }

        # D. Monospace / Code Block
        if font_name and any(cf in font_name.lower().replace(" ", "") for cf in cls.CODE_FONTS):
            return {
                "content_type": "code",
                "tag": "Code",
                "is_tagged": False,
                "tag_source": "layout_inference",
                "parameters": {
                    "content_type": "code",
                    "tag": "Code",
                    "is_tagged": False,
                    "tag_source": "layout_inference",
                    "font_name": font_name,
                    "font_size": effective_size,
                    "line_count": line_count,
                    "word_count": word_count,
                    "bbox": bbox
                }
            }

        # E. Explicit Section or Numbered Heading patterns
        if (cls.SECTION_HEADING_REGEX.match(clean_text) or cls.NUMBERED_HEADING_REGEX.match(clean_text)) and is_short_text:
            lvl = 1 if cls.SECTION_HEADING_REGEX.match(clean_text) else 2
            ctype = f"heading_{lvl}"
            return {
                "content_type": ctype,
                "tag": f"H{lvl}",
                "is_tagged": False,
                "tag_source": "layout_inference",
                "parameters": {
                    "content_type": ctype,
                    "tag": f"H{lvl}",
                    "is_tagged": False,
                    "tag_source": "layout_inference",
                    "level": lvl,
                    "heading_text": clean_text,
                    "font_size": effective_size,
                    "is_bold": is_bold,
                    "word_count": word_count,
                    "bbox": bbox
                }
            }

        # F. Typographic Font Hierarchy (Title, H1, H2, H3)
        if is_short_text and effective_size > 0:
            if effective_size >= max(20.0, median_body_size * 1.75):
                return {
                    "content_type": "title",
                    "tag": "Title",
                    "is_tagged": False,
                    "tag_source": "layout_inference",
                    "parameters": {
                        "content_type": "title",
                        "tag": "Title",
                        "is_tagged": False,
                        "tag_source": "layout_inference",
                        "level": 0,
                        "heading_text": clean_text,
                        "font_size": effective_size,
                        "is_bold": is_bold,
                        "word_count": word_count,
                        "character_count": char_count,
                        "bbox": bbox
                    }
                }
            if effective_size >= max(16.0, median_body_size * 1.4) or (is_bold and effective_size >= median_body_size * 1.3):
                return {
                    "content_type": "heading_1",
                    "tag": "H1",
                    "is_tagged": False,
                    "tag_source": "layout_inference",
                    "parameters": {
                        "content_type": "heading_1",
                        "tag": "H1",
                        "is_tagged": False,
                        "tag_source": "layout_inference",
                        "level": 1,
                        "heading_text": clean_text,
                        "font_size": effective_size,
                        "is_bold": is_bold,
                        "word_count": word_count,
                        "character_count": char_count,
                        "bbox": bbox
                    }
                }
            if effective_size >= max(13.5, median_body_size * 1.2) or (is_bold and effective_size >= median_body_size * 1.15):
                return {
                    "content_type": "heading_2",
                    "tag": "H2",
                    "is_tagged": False,
                    "tag_source": "layout_inference",
                    "parameters": {
                        "content_type": "heading_2",
                        "tag": "H2",
                        "is_tagged": False,
                        "tag_source": "layout_inference",
                        "level": 2,
                        "heading_text": clean_text,
                        "font_size": effective_size,
                        "is_bold": is_bold,
                        "word_count": word_count,
                        "character_count": char_count,
                        "bbox": bbox
                    }
                }
            if is_bold and effective_size >= median_body_size and word_count <= 15:
                return {
                    "content_type": "heading_3",
                    "tag": "H3",
                    "is_tagged": False,
                    "tag_source": "layout_inference",
                    "parameters": {
                        "content_type": "heading_3",
                        "tag": "H3",
                        "is_tagged": False,
                        "tag_source": "layout_inference",
                        "level": 3,
                        "heading_text": clean_text,
                        "font_size": effective_size,
                        "is_bold": is_bold,
                        "word_count": word_count,
                        "character_count": char_count,
                        "bbox": bbox
                    }
                }

        # G. Standard Paragraph (Body Text)
        tag_src = "pdf_struct_tree" if doc_is_tagged else ("ocr" if source == "ocr" else "layout_inference")
        return {
            "content_type": "paragraph",
            "tag": "P",
            "is_tagged": True if doc_is_tagged else False,
            "tag_source": tag_src,
            "parameters": {
                "content_type": "paragraph",
                "tag": "P",
                "is_tagged": True if doc_is_tagged else False,
                "tag_source": tag_src,
                "word_count": word_count,
                "character_count": char_count,
                "line_count": line_count,
                "font_name": font_name,
                "font_size": effective_size,
                "is_bold": is_bold,
                "is_italic": is_italic,
                "font_color": font_color,
                "bbox": bbox
            }
        }

    @classmethod
    def build_tagging_summary(cls, elements: List[ExtractedElement], doc_is_tagged: bool = False) -> TaggingSummary:
        total = len(elements)
        tagged_count = sum(1 for e in elements if getattr(e, "is_tagged", False))
        inferred_count = total - tagged_count

        content_types: Dict[str, int] = {}
        tag_sources: Dict[str, int] = {}

        for e in elements:
            ct = getattr(e, "content_type", None) or getattr(e, "type", "unknown")
            content_types[ct] = content_types.get(ct, 0) + 1

            ts = getattr(e, "tag_source", None) or "unknown"
            tag_sources[ts] = tag_sources.get(ts, 0) + 1

        if doc_is_tagged or (total > 0 and tagged_count == total):
            status = "tagged"
        elif tagged_count > 0:
            status = "partially_tagged"
        else:
            status = "untagged"

        return TaggingSummary(
            is_tagged_document=doc_is_tagged or (tagged_count > 0 and tagged_count >= total * 0.5),
            document_tag_status=status,
            total_elements=total,
            tagged_elements_count=tagged_count,
            inferred_elements_count=inferred_count,
            content_types=content_types,
            tag_sources=tag_sources
        )
