import re
import logging
from typing import List, Dict, Any, Optional, Callable
import docx
from lxml import etree

from app.originality.models import (
    PageOriginalityResult,
    VerificationType,
    MismatchItem,
    LineDiffItem,
)
from app.originality.normalizer import TextNormalizer
from app.originality.diff_engine import DiffEngine
from app.originality.accuracy import AccuracyCalculator

logger = logging.getLogger("docx_checker")

NAMESPACES = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'm': 'http://schemas.openxmlformats.org/officeDocument/2006/math',
    'v': 'urn:schemas-microsoft-com:vml',
    'w10': 'urn:schemas-microsoft-com:office:word',
}


class DOCXOriginalityChecker:
    """
    Verification for Microsoft Word (.docx) documents against extracted text.
    Inspects paragraphs, headings, tables, headers, footers, footnotes,
    and text boxes, dividing into sections or pages.
    """

    def check_docx(
        self,
        docx_path: str,
        extracted_text: str,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> List[PageOriginalityResult]:
        """
        Extracts structured sections from DOCX and performs line-by-line comparison with extracted text.
        """
        doc = docx.Document(docx_path)
        sections_data = self._extract_docx_sections(doc, docx_path)
        total_sections = max(1, len(sections_data))

        # Parse extracted text by page delimiters if available
        extracted_sections_map = self._split_extracted_text_by_sections(extracted_text, total_sections)

        page_results: List[PageOriginalityResult] = []

        for sec_idx, sec in enumerate(sections_data):
            page_num = sec_idx + 1
            if progress_callback:
                progress_callback(f"Processing Section/Page {page_num} of {total_sections}...", page_num, total_sections)

            ref_text = sec.get("text", "")
            ext_sec_text = extracted_sections_map.get(page_num, "")

            orig_lines = TextNormalizer.get_lines(ref_text)
            ext_lines = TextNormalizer.get_lines(ext_sec_text)

            orig_words = TextNormalizer.extract_words(ref_text)
            ext_words = TextNormalizer.extract_words(ext_sec_text)

            line_diffs, mismatches = DiffEngine.compare_page_lines(
                orig_lines=orig_lines,
                ext_lines=ext_lines,
                page_num=page_num,
                confidence=1.0
            )

            # Enrich mismatch locations with DOCX paragraph / table context
            for mm in mismatches:
                line_idx = mm.line - 1
                if 0 <= line_idx < len(sec.get("line_locations", [])):
                    mm.location = f"Section {page_num}, {sec['line_locations'][line_idx]}"

            accuracy, status = AccuracyCalculator.calculate_page_accuracy(
                orig_words=orig_words,
                ext_words=ext_words,
                mismatches=mismatches
            )

            page_results.append(PageOriginalityResult(
                page=page_num,
                orig_word_count=len(orig_words),
                extracted_word_count=len(ext_words),
                orig_char_count=sum(len(c) for c in orig_words),
                extracted_char_count=sum(len(c) for c in ext_words),
                accuracy=accuracy,
                status=status,
                verification_type=VerificationType.TEXT_BASED,
                mismatches=mismatches,
                orig_lines=orig_lines,
                extracted_lines=ext_lines,
                line_diffs=line_diffs
            ))

        return page_results

    def _extract_docx_sections(self, doc: docx.Document, docx_path: str) -> List[Dict[str, Any]]:
        """
        Extracts content divided into pages/sections by explicit page breaks, section breaks,
        or logical block groupings.
        """
        sections: List[Dict[str, Any]] = []
        current_lines: List[str] = []
        current_locations: List[str] = []

        def flush_section():
            if current_lines:
                sections.append({
                    "text": "\n".join(current_lines),
                    "line_locations": list(current_locations)
                })
                current_lines.clear()
                current_locations.clear()

        # 1. Header content from document sections
        for s_idx, sec in enumerate(doc.sections):
            if sec.header and sec.header.paragraphs:
                for h_p in sec.header.paragraphs:
                    txt = h_p.text.strip()
                    if txt:
                        current_lines.append(txt)
                        current_locations.append(f"Header {s_idx + 1}")

        # 2. Iterate through body elements (paragraphs and tables) in document sequence
        p_counter = 1
        t_counter = 1

        for child in doc.element.body:
            tag = child.tag.split('}')[-1]

            # Paragraph element (w:p)
            if tag == 'p':
                # Check for explicit hard page break: <w:br w:type="page"/>
                page_breaks = child.xpath('.//w:br[@w:type="page"]')
                if page_breaks:
                    flush_section()

                p_parts = []
                for n in child.xpath('.//w:t | .//w:tab'):
                    local_n = n.tag.split('}')[-1]
                    if local_n == 't' and n.text:
                        p_parts.append(n.text)
                    elif local_n == 'tab':
                        p_parts.append("\t")
                p_text = "".join(p_parts).strip()
                if p_text:
                    for sub_l in re.split(r'[\t\n]+', p_text):
                        sub_l = sub_l.strip()
                        if sub_l:
                            current_lines.append(sub_l)
                            current_locations.append(f"Paragraph {p_counter}")
                    p_counter += 1

                # Check for footnotes/endnotes
                fn_nodes = child.xpath('.//w:footnoteReference')
                if fn_nodes:
                    current_locations[-1] = f"Paragraph {p_counter - 1} (with Footnote)"

            # Table element (w:tbl)
            elif tag == 'tbl':
                row_nodes = child.xpath('.//w:tr')
                for r_idx, r in enumerate(row_nodes):
                    cell_nodes = r.xpath('.//w:tc')
                    cell_texts = []
                    for c_idx, c in enumerate(cell_nodes):
                        c_txt = " ".join(c.xpath('.//w:t/text()')).strip()
                        if c_txt:
                            cell_texts.append(c_txt)
                    if cell_texts:
                        row_line = " | ".join(cell_texts)
                        current_lines.append(row_line)
                        current_locations.append(f"Table {t_counter}, Row {r_idx + 1}")
                t_counter += 1

        # 3. Footer content from document sections
        for s_idx, sec in enumerate(doc.sections):
            if sec.footer and sec.footer.paragraphs:
                for f_p in sec.footer.paragraphs:
                    txt = f_p.text.strip()
                    if txt:
                        current_lines.append(txt)
                        current_locations.append(f"Footer {s_idx + 1}")

        flush_section()

        if not sections:
            sections.append({
                "text": "",
                "line_locations": []
            })

        return sections

    def _split_extracted_text_by_sections(
        self,
        extracted_text: str,
        total_sections: int
    ) -> Dict[int, str]:
        """
        Splits extracted text into sections matching DOCX sections.
        """
        sec_map: Dict[int, str] = {}
        if not extracted_text:
            return sec_map

        regex = re.compile(r'---\s*(?:Page|Section)\s*(\d+)\s*---', re.IGNORECASE)
        splits = regex.split(extracted_text)

        if len(splits) > 1:
            for i in range(1, len(splits), 2):
                try:
                    s_num = int(splits[i])
                    s_text = splits[i + 1].strip() if i + 1 < len(splits) else ""
                    sec_map[s_num] = s_text
                except (ValueError, IndexError):
                    pass

        if sec_map:
            return sec_map

        if total_sections <= 1:
            sec_map[1] = extracted_text.strip()
            return sec_map

        lines = extracted_text.strip().split('\n')
        lines_per_sec = max(1, len(lines) // total_sections)
        for s in range(1, total_sections + 1):
            start = (s - 1) * lines_per_sec
            end = s * lines_per_sec if s < total_sections else len(lines)
            sec_map[s] = "\n".join(lines[start:end]).strip()

        return sec_map
