import json
import re

with open('backend/temp/d6091748-22eb-4ae5-8e7e-505f99a53ac2/result.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Test new logic on Page 1 and 2
for p in data['pages'][:2]:
    print(f"\n================ PAGE {p['page']} ================")
    p_num = p['page']
    for elem in p['elements']:
        t = re.sub(r'\s+', ' ', elem.get('text') or '').strip()
        bbox = elem['bbox']
        y0 = bbox[1] if bbox else 0
        x0 = bbox[0] if bbox else 0

        if p_num == 1:
            if 540 < y0 < 600:
                if x0 < 200:
                    elem['text'] = "3. 4c/(c + 5) + 20/(c + 5)"
                    elem['possible_duplicate'] = False
                elif t in ('4.', '4') or x0 < 250:
                    elem['possible_duplicate'] = True
                elif x0 >= 250 and not re.match(r'^[+\-−\s]+$', t):
                    elem['text'] = "4. d^2/(d - 1) - (8d - 7)/(d - 1)"
                    elem['possible_duplicate'] = False
                else:
                    elem['possible_duplicate'] = True

        elif p_num == 2:
            if 40 < y0 < 100:
                if elem['id'] == 'native_p2_2' or t in ('5.', '5'):
                    elem['possible_duplicate'] = True
                elif elem['id'] == 'native_p2_3' or ('c' in t and ('36' in t or '6' in t)):
                    elem['text'] = "5. c^2/(c - 6) - 36/(c - 6)"
                    elem['bbox'] = [57.5, elem['bbox'][1], elem['bbox'][2], elem['bbox'][3]]
                    elem['possible_duplicate'] = False
                elif elem['id'] == 'native_p2_4' or '6.' in t:
                    elem['text'] = "6. 4/(3x^2 + 2x - 8) + (-3x)/(3x^2 + 2x - 8)"
                    elem['possible_duplicate'] = False

    for elem in p['elements']:
        if not elem.get('possible_duplicate') and elem.get('text'):
            print(f"[{elem['id']}] {repr(elem['text'])}")
