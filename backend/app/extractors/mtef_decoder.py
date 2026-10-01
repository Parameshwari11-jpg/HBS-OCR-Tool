import io
import re
import logging
import zipfile
from typing import Dict, Any, Optional

logger = logging.getLogger("mtef_decoder")


def clean_math_term(s: str) -> str:
    """
    Cleans up exponents and indices, e.g. turning ^{2} into ^2, _{1} into _1.
    """
    s = s.strip()
    s = re.sub(r'\^\{([a-zA-Z0-9]+)\}', r'^\1', s)
    s = re.sub(r'\_\{([a-zA-Z0-9]+)\}', r'_\1', s)
    return s


def _needs_parens(expr: str) -> bool:
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
    body = expr[1:] if expr[0] in ('+', '-') else expr
    return bool(re.search(r'[\+\-\=]', body))


def format_fraction(num: str, den: str) -> str:
    """
    Formats fractions mathematically correctly:
    Compound expressions in numerator or denominator (containing + or -) are parenthesized,
    e.g. (p + r)/q, (p - r)/q, 3a/(a - 4), (a + 8)/(a - 4).
    Single-term numerators and denominators (e.g. p/q, 7/10) remain clean without parentheses.
    """
    num = clean_math_term(num).strip()
    den = clean_math_term(den).strip()
    n_str = f"({num})" if _needs_parens(num) else num
    d_str = f"({den})" if _needs_parens(den) else den
    return f"{n_str}/{d_str}"


class MTEFDecoder:
    """
    Decodes MathType MTEF (MathType Equation Format) binary streams from OLE objects
    into clean, human-readable mathematical text matching original document order and styling.
    Supports MTEF v3, v4, and v5.
    """
    def __init__(self, data: bytes):
        self.raw_data = data
        self.data = b""
        self.pos = 0

    def decode(self) -> str:
        if len(self.raw_data) < 28:
            return ""
        hdr_size = int.from_bytes(self.raw_data[:4], 'little')
        if hdr_size >= len(self.raw_data) or hdr_size < 4:
            hdr_size = 28
        self.data = self.raw_data[hdr_size:]
        self.pos = 0

        if len(self.data) < 5 or self.data[0] not in (3, 4, 5):
            return ""

        # Search for root equation record (LINE+PILE: b'\x01\x00\x04\x00\x00\x0a')
        pile_idx = self.data.find(b'\x01\x00\x04\x00\x00\x0a')
        if pile_idx != -1:
            self.pos = pile_idx
        else:
            self.pos = 20
            while self.pos < len(self.data) - 2:
                if self.data[self.pos] == 1 and self.data[self.pos + 1] == 0:
                    break
                self.pos += 1

        if self.pos >= len(self.data):
            return ""

        result = self._parse_node()
        result = clean_math_term(result)
        result = re.sub(r' +', ' ', result).strip()
        result = result.replace('+ -', '-').replace('- +', '-')
        return result

    def _read_byte(self) -> int:
        if self.pos < len(self.data):
            b = self.data[self.pos]
            self.pos += 1
            return b
        return 0

    def _read_signed_int(self) -> int:
        b = self._read_byte()
        if b == 128:  # Large integer (3 bytes)
            b1 = self._read_byte()
            b2 = self._read_byte()
            val = b1 | (b2 << 8)
            if val >= 32768:
                val -= 65536
            return val
        return b - 128

    def _skip_nudge(self):
        b1 = self._read_byte()
        b2 = self._read_byte()
        if b1 == 128 and b2 == 128:
            self.pos += 4

    def _parse_line(self) -> str:
        opt = self._read_byte()
        if opt & 0x08:
            self._skip_nudge()
        if opt & 0x04:
            self.pos += 2  # line spacing
        if opt & 0x02:
            pass  # ruler
        if opt & 0x01:
            return ""  # null line

        parts = []
        while self.pos < len(self.data):
            if self.data[self.pos] == 0:  # END of line
                self.pos += 1
                break
            parts.append(self._parse_node())
        return "".join(parts)

    def _parse_node(self) -> str:
        if self.pos >= len(self.data):
            return ""
        tag = self._read_byte()

        if tag == 0:  # END
            return ""

        elif tag == 1:  # LINE
            return self._parse_line()

        elif tag == 2:  # CHAR
            opt = self._read_byte()
            if opt & 0x08:
                self._skip_nudge()
            tf = self._read_signed_int()
            mtcode = 0
            if not (opt & 0x20):
                c1 = self._read_byte()
                c2 = self._read_byte()
                mtcode = c1 | (c2 << 8)
            if opt & 0x04:
                self._read_byte()  # 8-bit font pos
            elif opt & 0x10:
                self.pos += 2  # 16-bit font pos
            if opt & 0x01:  # embellishment list
                while self.pos < len(self.data):
                    if self._read_byte() == 0:
                        break

            if mtcode in (0x2212, 0x2d):
                return " - "
            elif mtcode == 0x2b:
                return " + "
            elif mtcode == 0x3d:
                return " = "
            elif mtcode == 0x2260:
                return " \u2260 "
            elif mtcode == 0x00b1:
                return " \u00b1 "
            elif mtcode == 0x00d7:
                return " \u00d7 "
            elif mtcode == 0x00f7:
                return " \u00f7 "
            elif mtcode == 0x2264:
                return " \u2264 "
            elif mtcode == 0x2265:
                return " \u2265 "
            elif mtcode == 0x221e:
                return " \u221e "
            elif 32 <= mtcode <= 126:
                return chr(mtcode)
            elif mtcode != 0:
                try:
                    return chr(mtcode)
                except Exception:
                    return ""
            return ""

        elif tag == 3:  # TMPL (template)
            opt = self._read_byte()
            if opt & 0x08:
                self._skip_nudge()
            sel = self._read_byte()
            var = self._read_byte()
            if var & 0x80:
                var = (var & 0x7f) | (self._read_byte() << 8)
            tmpl_opt = self._read_byte()

            # Collect subobjects until tag 0 (END)
            sub_lines = []
            while self.pos < len(self.data):
                if self.data[self.pos] == 0:
                    self.pos += 1
                    break
                sub_lines.append(self._parse_node())

            # Fraction: 11 (tmFRACT)
            if sel == 11 or sel == 0x0b:
                lines = [l.strip() for l in sub_lines if l.strip()]
                num = lines[0] if len(lines) > 0 else ""
                den = lines[1] if len(lines) > 1 else ""
                return format_fraction(num, den)

            # Superscript: 28 (tmSUP) or 3
            elif sel == 28 or sel == 3:
                lines = [l.strip() for l in sub_lines if l.strip()]
                sup = lines[-1] if lines else ""
                sup = clean_math_term(sup)
                if len(sup) == 1 and sup.isalnum():
                    return f"^{sup}"
                return f"^{{{sup}}}"

            # Subscript: 27 (tmSUB) or 2
            elif sel == 27 or sel == 2:
                lines = [l.strip() for l in sub_lines if l.strip()]
                sub = lines[0] if lines else ""
                sub = clean_math_term(sub)
                if len(sub) == 1 and sub.isalnum():
                    return f"_{sub}"
                return f"_{{{sub}}}"

            # Sub/Superscript: 29 (tmSUBSUP) or 1
            elif sel == 29 or sel == 1:
                lines = [l.strip() for l in sub_lines if l.strip()]
                sub = lines[0] if len(lines) > 0 else ""
                sup = lines[1] if len(lines) > 1 else ""
                sub = clean_math_term(sub)
                sup = clean_math_term(sup)
                sub_str = f"_{sub}" if len(sub) == 1 else f"_{{{sub}}}"
                sup_str = f"^{sup}" if len(sup) == 1 else f"^{{{sup}}}"
                return f"{sub_str}{sup_str}"

            # Square Root: 10 (tmROOT) or 4 or 24
            elif sel in (10, 4, 24):
                lines = [l.strip() for l in sub_lines if l.strip()]
                rad = lines[-1] if lines else ""
                return f"\u221a({rad})"

            # Fences / Brackets / Parentheses
            elif sel == 0:  # tmPAREN: ( ... )
                inner = " ".join([l.strip() for l in sub_lines if l.strip()])
                return f"({inner})"

            elif sel == 1:  # tmBRACK: [ ... ]
                inner = " ".join([l.strip() for l in sub_lines if l.strip()])
                return f"[{inner}]"

            elif sel == 2:  # tmBRACE: { ... }
                inner = " ".join([l.strip() for l in sub_lines if l.strip()])
                return f"{{{inner}}}"

            elif sel == 3:  # tmBAR: | ... |
                inner = " ".join([l.strip() for l in sub_lines if l.strip()])
                return f"|{inner}|"

            else:
                return " ".join([l.strip() for l in sub_lines if l.strip()])

        elif tag == 4:  # PILE
            opt = self._read_byte()
            if opt & 0x08:
                self._skip_nudge()
            halign = self._read_byte()
            valign = self._read_byte()
            lines = []
            while self.pos < len(self.data):
                if self.data[self.pos] == 0:
                    self.pos += 1
                    break
                lines.append(self._parse_node())
            return " \n ".join([l.strip() for l in lines if l.strip()])

        elif tag in (10, 11, 12, 13, 14):  # TYPESIZE: single-byte records (0 extra bytes)
            return ""

        elif tag == 9:  # SIZE
            b = self._read_byte()
            if b == 101:
                self.pos += 2
            elif b == 100:
                self.pos += 3
            else:
                self.pos += 1
            return ""

        elif tag == 8:  # FONT_STYLE_DEF
            self._read_byte()
            self._read_byte()
            return ""

        elif tag == 6:  # EMBELL
            opt = self._read_byte()
            if opt & 0x08:
                self._skip_nudge()
            self._read_byte()
            return ""

        elif tag == 5:  # MATRIX
            self.pos += 2
            return "[matrix]"

        else:
            return ""


def extract_docx_mathtype_equations(docx_path: str) -> Dict[str, str]:
    """
    Extracts and decodes all MathType equations embedded in a DOCX file.
    Returns a dict mapping the relative target (e.g. 'embeddings/oleObject1.bin')
    to the cleanly decoded formula string.
    """
    ole_map: Dict[str, str] = {}
    try:
        import olefile
        with zipfile.ZipFile(docx_path, 'r') as z:
            for name in z.namelist():
                if name.startswith('word/embeddings/oleObject'):
                    target_key = name.replace('word/', '')
                    try:
                        b = z.read(name)
                        ole = olefile.OleFileIO(io.BytesIO(b))
                        for item in ole.listdir():
                            if 'Equation' in item[0]:
                                raw_eq = ole.openstream(item).read()
                                decoder = MTEFDecoder(raw_eq)
                                decoded_text = decoder.decode()
                                if decoded_text:
                                    ole_map[target_key] = decoded_text
                                break
                    except Exception as e:
                        logger.warning(f"Failed to decode MathType in {name}: {e}")
    except Exception as e:
        logger.warning(f"Error accessing docx embeddings for MathType: {e}")

    return ole_map
