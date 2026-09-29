import zipfile, io, re
from lxml import etree
from app.extractors.mtef_decoder import extract_docx_mathtype_equations

def inspect_doc_order():
    docx_path = 'backend/uploads/fe6d8d56-abec-46a9-8e83-c2f776f4e95d.docx'
    ole_texts = extract_docx_mathtype_equations(docx_path)

    with zipfile.ZipFile(docx_path, 'r') as z:
        rels_xml = z.read('word/_rels/document.xml.rels')
        rels_tree = etree.fromstring(rels_xml)
        rel_map = {r.get('Id'): r.get('Target') for r in rels_tree if r.get('Id') and r.get('Target')}

        doc_xml = z.read('word/document.xml')
        tree = etree.fromstring(doc_xml)
        namespaces = {
            'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
            'o': 'urn:schemas-microsoft-com:office:office',
            'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
        }

        body = tree.find('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}body')
        for idx, child in enumerate(body):
            tag = child.tag.split('}')[-1]
            if tag == 'p':
                parts = []
                for node in child.iter():
                    ntag = node.tag.split('}')[-1]
                    if ntag == 't' and node.text:
                        parts.append(node.text)
                    elif ntag == 'OLEObject':
                        rid = node.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
                        target = rel_map.get(rid, '')
                        if target in ole_texts:
                            parts.append(f' {ole_texts[target]} ')
                text = ' '.join(''.join(parts).split()).strip()
                if text:
                    print(f'{idx}: [P] {ascii(text)}')
            elif tag == 'tbl':
                rows = child.xpath('.//w:tr', namespaces=namespaces)
                print(f'{idx}: [TBL] Table with {len(rows)} rows')
                for r_idx, r in enumerate(rows):
                    cells = r.xpath('.//w:tc', namespaces=namespaces)
                    cell_texts = []
                    for c in cells:
                        c_parts = []
                        for node in c.iter():
                            ntag = node.tag.split('}')[-1]
                            if ntag == 't' and node.text:
                                c_parts.append(node.text)
                            elif ntag == 'OLEObject':
                                rid = node.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
                                target = rel_map.get(rid, '')
                                if target in ole_texts:
                                    c_parts.append(f' {ole_texts[target]} ')
                        cell_texts.append(' '.join(''.join(c_parts).split()).strip())
                    print(f'   Row {r_idx+1}: {ascii(cell_texts)}')

if __name__ == '__main__':
    inspect_doc_order()
