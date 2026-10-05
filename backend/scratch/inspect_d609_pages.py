import json

with open('backend/temp/d6091748-22eb-4ae5-8e7e-505f99a53ac2/result.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for p in data['pages']:
    print(f"\n=== PAGE {p['page']} ===")
    for i, el in enumerate(p['elements']):
        dup = el.get('possible_duplicate')
        bbox = [round(x, 1) for x in el['bbox']]
        txt = repr(el.get('text', '')[:100] if el.get('text') else '')
        print(f"{i:2d}: id={el['id']:15s} dup={str(dup):5s} bbox={bbox} text={txt}")
