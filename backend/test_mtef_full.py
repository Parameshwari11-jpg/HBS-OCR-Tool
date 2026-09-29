import zipfile, io, olefile

class MTEFParser:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def parse(self) -> str:
        # Find MTEF start
        if len(self.data) < 28:
            return ""
        hdr_size = int.from_bytes(self.data[:4], 'little')
        if hdr_size >= len(self.data):
            hdr_size = 28
        mtef = self.data[hdr_size:]
        self.data = mtef
        self.pos = 0

        # MTEF header: ver (1 byte), plat (1 byte), prod (1 byte), prod_ver (1 byte), prod_subver (1 byte)
        if len(self.data) < 5 or self.data[0] not in (3, 4, 5):
            return ""
        self.pos = 5
        # Skip app key (null-terminated)
        while self.pos < len(self.data) and self.data[self.pos] != 0:
            self.pos += 1
        self.pos += 1 # skip null
        if self.pos < len(self.data):
            self.pos += 1 # skip eq options byte

        # Skip font/size/ruler header until the root LINE tag (0x01)
        # In MTEF, the equation content starts with a LINE (tag 1)
        while self.pos < len(self.data):
            # The start of the equation body is a LINE record (tag 1)
            # which is followed by options (1 byte) and then records
            if self.data[self.pos] == 1 and self.pos > 15:
                # Check if next byte could be options and then a char or tmpl
                if self.pos + 2 < len(self.data) and self.data[self.pos+2] in (1, 2, 3, 4, 5, 0):
                    break
            self.pos += 1

        if self.pos >= len(self.data):
            # Fallback: scan for any tag 1
            for p in range(5, len(self.data)):
                if self.data[p] == 1:
                    self.pos = p
                    break

        return self.parse_line()

    def parse_line(self) -> str:
        if self.pos >= len(self.data):
            return ""
        tag = self.data[self.pos]
        if tag == 1: # LINE tag
            self.pos += 1
            # options byte
            if self.pos < len(self.data):
                options = self.data[self.pos]
                self.pos += 1
                # If nudge options present, skip nudge bytes
                if options & 0x08: # nudge
                    self.pos += 2

        tokens = []
        while self.pos < len(self.data):
            rec_tag = self.data[self.pos]
            if rec_tag == 0: # END
                self.pos += 1
                break
            elif rec_tag == 1: # nested LINE
                tokens.append(self.parse_line())
            elif rec_tag == 2: # CHAR
                self.pos += 1
                char_str = self.parse_char()
                if char_str:
                    tokens.append(char_str)
            elif rec_tag == 3: # TMPL (template)
                self.pos += 1
                tmpl_str = self.parse_tmpl()
                if tmpl_str:
                    tokens.append(tmpl_str)
            elif rec_tag == 4: # PILE
                self.pos += 1
                pile_str = self.parse_pile()
                if pile_str:
                    tokens.append(pile_str)
            elif rec_tag == 5: # MATRIX
                self.pos += 1
                tokens.append(self.parse_matrix())
            elif rec_tag == 6: # EMBEL
                self.pos += 1
                # embellishment has options + embel type
                self.pos += 2
            elif rec_tag == 8: # FONT style change
                self.pos += 2
            elif rec_tag == 9: # COLOR
                self.pos += 2
            else:
                # unknown tag, advance
                self.pos += 1

        return "".join(tokens)

    def parse_char(self) -> str:
        if self.pos >= len(self.data):
            return ""
        options = self.data[self.pos]
        self.pos += 1
        
        # Nudge check
        if options & 0x08:
            self.pos += 2
            
        # Typeface index
        typeface = 0
        if self.pos < len(self.data):
            typeface = self.data[self.pos]
            self.pos += 1
            if typeface & 0x80:
                pass # 1-byte typeface index

        # Character code (16-bit unicode or 8-bit ASCII)
        ch_str = ""
        if self.pos < len(self.data):
            c1 = self.data[self.pos]
            self.pos += 1
            c2 = 0
            if self.pos < len(self.data) and not (options & 0x01): # 16-bit char
                c2 = self.data[self.pos]
                self.pos += 1
                val = c1 | (c2 << 8)
            else:
                val = c1

            # Map symbols / Greek or standard chars
            if val == 0x2212 or val == 0x2d:
                ch_str = "-"
            elif val == 0x2b:
                ch_str = "+"
            elif val == 0x3d:
                ch_str = "="
            elif val == 0x2260 or val == 0x22: # \neq
                ch_str = " != "
            elif val == 0x00d7:
                ch_str = " * "
            elif val == 0x00f7:
                ch_str = " / "
            elif 32 <= val <= 126:
                ch_str = chr(val)
            else:
                try:
                    ch_str = chr(val)
                except Exception:
                    ch_str = ""

        return ch_str

    def parse_tmpl(self) -> str:
        if self.pos >= len(self.data):
            return ""
        options = self.data[self.pos]
        self.pos += 1
        if options & 0x08:
            self.pos += 2 # nudge
            
        selector = 0
        if self.pos < len(self.data):
            selector = self.data[self.pos]
            self.pos += 1
            
        variation = 0
        if self.pos < len(self.data):
            variation = self.data[self.pos]
            self.pos += 1

        # Template types
        # 11: Fraction
        if selector == 11 or selector == 0x0b:
            num = self.parse_line()
            den = self.parse_line()
            # Skip until end of tmpl (0x00)
            while self.pos < len(self.data) and self.data[self.pos] != 0:
                self.pos += 1
            if self.pos < len(self.data) and self.data[self.pos] == 0:
                self.pos += 1
            return f"({num})/({den})"
        
        # 4: Square Root
        elif selector == 4:
            content = self.parse_line()
            while self.pos < len(self.data) and self.data[self.pos] != 0:
                self.pos += 1
            if self.pos < len(self.data) and self.data[self.pos] == 0:
                self.pos += 1
            return f"sqrt({content})"
            
        # 0: Parentheses / Brackets
        elif selector == 0:
            content = self.parse_line()
            while self.pos < len(self.data) and self.data[self.pos] != 0:
                self.pos += 1
            if self.pos < len(self.data) and self.data[self.pos] == 0:
                self.pos += 1
            return f"({content})"
            
        # 1: Sub/Superscript
        elif selector in (1, 2, 3):
            # sub/sup has 1 or 2 lines
            sub_sup = self.parse_line()
            while self.pos < len(self.data) and self.data[self.pos] != 0:
                self.pos += 1
            if self.pos < len(self.data) and self.data[self.pos] == 0:
                self.pos += 1
            return f"^{{{sub_sup}}}" if selector == 3 else f"_{{{sub_sup}}}"
            
        else:
            # General template: parse contents until end
            parts = []
            while self.pos < len(self.data) and self.data[self.pos] != 0:
                parts.append(self.parse_line())
            if self.pos < len(self.data) and self.data[self.pos] == 0:
                self.pos += 1
            return " ".join([p for p in parts if p])

    def parse_pile(self) -> str:
        # Pile of lines
        self.pos += 1 # skip pile options
        lines = []
        while self.pos < len(self.data) and self.data[self.pos] != 0:
            lines.append(self.parse_line())
        if self.pos < len(self.data) and self.data[self.pos] == 0:
            self.pos += 1
        return "\n".join(lines)

    def parse_matrix(self) -> str:
        # Matrix
        self.pos += 2
        return "[matrix]"

def test_all():
    with zipfile.ZipFile('backend/uploads/fe6d8d56-abec-46a9-8e83-c2f776f4e95d.docx', 'r') as z:
        for i in range(1, 20):
            fname = f'word/embeddings/oleObject{i}.bin'
            if fname in z.namelist():
                b = z.read(fname)
                ole = olefile.OleFileIO(io.BytesIO(b))
                raw_eq = ole.openstream('Equation Native').read()
                parser = MTEFParser(raw_eq)
                res = parser.parse()
                print(f"oleObject{i:02d}: {ascii(res)}")

if __name__ == '__main__':
    test_all()
