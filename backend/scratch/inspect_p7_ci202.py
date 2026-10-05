import json

with open('backend/temp/f96caa41-6027-4f43-b1a7-41ff82226c3c/result.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

p7 = [p for p in data['pages'] if p['page'] == 7][0]
for e in sorted(p7['elements'], key=lambda x: x.get('reading_order') or 999):
    if not e.get('possible_duplicate') and e.get('text'):
        bbox = [round(x, 1) for x in e['bbox']]
        ro = e.get('reading_order')
        print(f"ro={ro}: bbox={bbox} id={e['id']} text={repr(e['text'])}")
