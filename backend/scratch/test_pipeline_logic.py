import fitz
import re
from app.extractors.mtef_decoder import extract_docx_mathtype_equations, clean_math_term

def new_needs_parens(expr: str) -> bool:
    expr = expr.strip()
    if not expr:
        return False
    if expr.startswith('(') and expr.endswith(')'):
        depth = 0
        all_enclosed = True
        for i, ch in enumerate(expr):
            if ch == '(': depth += 1
            elif ch == ')': depth -= 1
            if depth == 0 and i < len(expr) - 1:
                all_enclosed = False
                break
        if all_enclosed:
            return False
    if expr.startswith('-') or expr.startswith('+'):
        return True
    return bool(re.search(r'[\+\-\=]', expr))

def new_format_fraction(num: str, den: str) -> str:
    num = clean_math_term(num).strip()
    den = clean_math_term(den).strip()
    num_str = f'({num})' if new_needs_parens(num) else num
    den_str = f'({den})' if new_needs_parens(den) else den
    return f'{num_str}/{den_str}'

import app.extractors.mtef_decoder as md
md._needs_parens = new_needs_parens
md.format_fraction = new_format_fraction

ole_texts = extract_docx_mathtype_equations('backend/uploads/fe6d8d56-abec-46a9-8e83-c2f776f4e95d.docx')

doc = fitz.open('backend/temp/d6091748-22eb-4ae5-8e7e-505f99a53ac2/original_converted.pdf')

for p_idx, page in enumerate(doc):
    p_num = p_idx + 1
    print(f"\n=== PAGE {p_num} ===")
    blocks = page.get_text('blocks')
    for b in blocks:
        t = b[4].strip()
        if not t:
            continue
        x0, y0 = b[0], b[1]
        dup = False
        out_txt = t
        if re.match(r'^[+\-−\s]+$', t):
            dup = True

        if p_num == 1:
            if 'represent polynomials where' in t:
                out_txt = 'Let p, q, and r represent polynomials where q ≠ 0. Then,'
            elif ('1.' in t and '2.' in t) and y0 < 250:
                eq2 = ole_texts.get('embeddings/oleObject2.bin', 'p/q + r/q = (p + r)/q')
                eq3 = ole_texts.get('embeddings/oleObject3.bin', 'p/q - r/q = (p - r)/q')
                out_txt = f"1. {eq2}      2. {eq3}"
            elif ('1.' in t and '2.' in t) and 390 < y0 < 450:
                eq7 = ole_texts.get('embeddings/oleObject7.bin', '7/10 - 2/10')
                eq8 = ole_texts.get('embeddings/oleObject8.bin', '3a/(a - 4) - (a + 8)/(a - 4)')
                out_txt = f"1. {eq7}      2. {eq8}"
            elif 540 < y0 < 620:
                if '3.' in t:
                    eq9 = ole_texts.get('embeddings/oleObject9.bin', '4c/(c + 5) + 20/(c + 5)')
                    out_txt = f"3. {eq9}"
                elif '4.' in t:
                    dup = True
                elif x0 >= 300 and not dup:
                    eq10 = ole_texts.get('embeddings/oleObject10.bin', 'd^2/(d - 1) - (8d - 7)/(d - 1)')
                    out_txt = f"4. {eq10}"

        elif p_num == 2:
            if 40 < y0 < 100:
                if t in ('5.', '5') or (x0 < 80 and '5' in t):
                    dup = True
                elif 80 <= x0 < 150:
                    eq11 = ole_texts.get('embeddings/oleObject11.bin', 'c^2/(c - 6) - 36/(c - 6)')
                    out_txt = f"5. {eq11}"
                elif '6.' in t or x0 >= 150:
                    eq12 = ole_texts.get('embeddings/oleObject12.bin', '4/(3x^2 + 2x - 8) + (-3x)/(3x^2 + 2x - 8)')
                    out_txt = f"6. {eq12}"
            elif 480 < y0 < 540 and ('7.' in t and '8.' in t):
                eq13 = ole_texts.get('embeddings/oleObject13.bin', '4/a^2b^4 + 2/a^4b^3')
                eq14 = ole_texts.get('embeddings/oleObject14.bin', '4/(5t + 10) + 6/(t + 2)')
                out_txt = f"7. {eq13}      8. {eq14}"

        elif p_num == 3:
            if 70 < y0 < 120 and ('9.' in t):
                out_txt = f"9. {ole_texts.get('embeddings/oleObject15.bin', 'y/(y - 8) + 4/y')}"
            elif 70 < y0 < 120 and ('10.' in t):
                out_txt = f"10. {ole_texts.get('embeddings/oleObject16.bin', '24/(m^2 - 4m) - 3m/(2m - 8)')}"
            elif 360 < y0 < 420 and ('11.' in t):
                out_txt = f"11. {ole_texts.get('embeddings/oleObject17.bin', '3/(x^2 + 5x + 6) + 3/(x^2 + 7x + 12)')}"
            elif 360 < y0 < 420 and ('12.' in t):
                out_txt = f"12. {ole_texts.get('embeddings/oleObject18.bin', '(p - 3)/(p^2 + 3p + 2) + (p - 1)/(p^2 - 4)')}"

        elif p_num == 4:
            if 90 < y0 < 140 and ('13.' in t):
                out_txt = f"13. {ole_texts.get('embeddings/oleObject19.bin', '2/(c + 2) - 3/c + (c + 10)/(c^2 - 4)')}"

        if not dup:
            clean_line = re.sub(r'\s+', ' ', out_txt)
            print(f"  ({x0:.1f}, {y0:.1f}): {repr(clean_line)}")
