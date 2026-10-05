from app.extractors.xml_extractor import extract_docx_xml_content

items = extract_docx_xml_content('backend/uploads/fe6d8d56-abec-46a9-8e83-c2f776f4e95d.docx')
for item in items:
    if item['type'] == 'paragraph_with_math':
        print(f"{item['id']}: {item['text']}")
