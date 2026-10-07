import logging
import zipfile
import re
from typing import List, Dict, Any
from lxml import etree

from app.extractors.mtef_decoder import extract_docx_mathtype_equations

logger = logging.getLogger("xml_extractor")

NAMESPACES = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'wp': 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'pic': 'http://schemas.openxmlformats.org/drawingml/2006/picture',
    'v': 'urn:schemas-microsoft-com:vml',
    'm': 'http://schemas.openxmlformats.org/officeDocument/2006/math',
    'o': 'urn:schemas-microsoft-com:office:office',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
}

def extract_docx_xml_content(docx_file_path: str) -> List[Dict[str, Any]]:
    """
    Inspects underlying DOCX XML structures to extract text from:
    - MathType equations (decoded from MTEF binary streams in word/embeddings/)
    - OMML formulas (m:oMath, m:oMathPara)
    - Full paragraphs with inline equations seamlessly integrated
    - Text boxes (w:txbxContent, v:textbox)
    - Shapes & drawings (w:drawing, a:graphic)
    - Footnotes (w:footnote)
    """
    results: List[Dict[str, Any]] = []
    try:
        # 1. Decode all MathType equations from word/embeddings/oleObject*.bin
        ole_texts = extract_docx_mathtype_equations(docx_file_path)

        with zipfile.ZipFile(docx_file_path, 'r') as z:
            rel_map = {}
            if 'word/_rels/document.xml.rels' in z.namelist():
                rels_xml = z.read('word/_rels/document.xml.rels')
                rels_tree = etree.fromstring(rels_xml)
                for r in rels_tree:
                    rel_id = r.get('Id')
                    target = r.get('Target')
                    if rel_id and target:
                        rel_map[rel_id] = target

            # 2. Inspect document.xml
            if 'word/document.xml' in z.namelist():
                doc_xml = z.read('word/document.xml')
                tree = etree.fromstring(doc_xml)

                # Individual MathType OLE Objects
                ole_nodes = tree.xpath('//o:OLEObject[contains(@ProgID, "Equation") or contains(@ProgID, "MathType")] | //w:object', namespaces=NAMESPACES)
                for idx, ole in enumerate(ole_nodes):
                    r_id = ole.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
                    target = rel_map.get(r_id, '')
                    formula_text = ole_texts.get(target, '')
                    if formula_text:
                        results.append({
                            "id": f"docx_mathtype_{idx+1}",
                            "type": "formula",
                            "source": "mathtype",
                            "subtype": "mathtype_ole",
                            "prog_id": ole.get('ProgID', 'Equation'),
                            "rel_id": r_id,
                            "text": formula_text
                        })

                # Individual OMML Equations (m:oMath, m:oMathPara)
                math_nodes = tree.xpath('//m:oMath | //m:oMathPara', namespaces=NAMESPACES)
                for idx, m_node in enumerate(math_nodes):
                    m_texts = m_node.xpath('.//m:t/text() | .//w:t/text()', namespaces=NAMESPACES)
                    formula_text = "".join(m_texts).strip()
                    if formula_text:
                        results.append({
                            "id": f"docx_omml_{idx+1}",
                            "type": "formula",
                            "source": "docx_xml",
                            "subtype": "omml_equation",
                            "text": formula_text
                        })

                # Full Paragraphs with inline MathType & text reconstructed in exact sequence
                p_nodes = tree.xpath('//w:p', namespaces=NAMESPACES)
                for p_idx, p in enumerate(p_nodes):
                    # Skip outer container paragraphs that wrap nested paragraphs to avoid duplication
                    if p.xpath('.//w:p', namespaces=NAMESPACES):
                        continue
                    p_parts = []
                    has_math = False
                    for node in p.iter():
                        tag = node.tag.split('}')[-1]
                        if tag == 't' and node.text:
                            p_parts.append(node.text)
                        elif tag == 'OLEObject':
                            r_id = node.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
                            target = rel_map.get(r_id, '')
                            if target in ole_texts:
                                p_parts.append(f" {ole_texts[target]} ")
                                has_math = True
                        elif tag == 'oMath':
                            m_texts = node.xpath('.//m:t/text() | .//w:t/text()', namespaces=NAMESPACES)
                            m_str = "".join(m_texts).strip()
                            if m_str:
                                p_parts.append(f" {m_str} ")
                                has_math = True

                    from app.utils.spacing_engine import merge_tokens as merge_xml_tokens
                    raw_line = merge_xml_tokens(p_parts).strip() if p_parts else ""
                    full_line = re.sub(r'\s+', ' ', raw_line)
                    if full_line and has_math:
                        results.append({
                            "id": f"docx_math_p_{p_idx+1}",
                            "type": "paragraph_with_math",
                            "source": "docx_xml",
                            "text": full_line
                        })

                # Textboxes
                txbx_nodes = tree.xpath('//w:txbxContent', namespaces=NAMESPACES)
                for idx, txbx in enumerate(txbx_nodes):
                    text_lines = txbx.xpath('.//w:t/text()', namespaces=NAMESPACES)
                    full_text = " ".join(text_lines).strip()
                    if full_text:
                        results.append({
                            "id": f"docx_xml_txbx_{idx+1}",
                            "type": "textbox",
                            "source": "docx_xml",
                            "text": full_text
                        })

                # Shapes & Drawings
                drawing_nodes = tree.xpath('//w:drawing | //v:shape', namespaces=NAMESPACES)
                for idx, dwg in enumerate(drawing_nodes):
                    text_lines = dwg.xpath('.//w:t/text()', namespaces=NAMESPACES)
                    full_text = " ".join(text_lines).strip()
                    if full_text and not any(full_text in r.get("text", "") for r in results):
                        results.append({
                            "id": f"docx_xml_shape_{idx+1}",
                            "type": "shape",
                            "source": "docx_xml",
                            "text": full_text
                        })

            # 3. Inspect footnotes.xml
            if 'word/footnotes.xml' in z.namelist():
                fn_xml = z.read('word/footnotes.xml')
                fn_tree = etree.fromstring(fn_xml)
                footnotes = fn_tree.xpath('//w:footnote', namespaces=NAMESPACES)
                for idx, fn in enumerate(footnotes):
                    fn_type = fn.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}type')
                    if fn_type not in ('separator', 'continuationSeparator'):
                        text_lines = fn.xpath('.//w:t/text()', namespaces=NAMESPACES)
                        full_text = " ".join(text_lines).strip()
                        if full_text:
                            results.append({
                                "id": f"docx_xml_footnote_{idx+1}",
                                "type": "footnote",
                                "source": "docx_xml",
                                "text": full_text
                            })

    except Exception as e:
        logger.error(f"Error inspecting DOCX XML: {e}", exc_info=True)

    return results
