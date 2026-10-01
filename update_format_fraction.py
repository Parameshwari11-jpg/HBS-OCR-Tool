import re

path = 'backend/app/extractors/mtef_decoder.py'
with open(path, 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()

pattern = r'def format_fraction\(num: str, den: str\) -> str:[\s\S]*?return f"\{n_str\}/\{d_str\}"'
replacement = '''def format_fraction(num: str, den: str) -> str:
    """
    Formats fractions cleanly as num/den without adding artificial parentheses.
    Extracts the exact equation as present in the original document.
    """
    num = clean_math_term(num).strip()
    den = clean_math_term(den).strip()
    return f"{num}/{den}"'''

new_content = re.sub(pattern, replacement, content, count=1)
if new_content != content:
    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("SUCCESS: format_fraction updated!")
else:
    print("ERROR: Pattern not matched!")
