import re
import unittest

def is_math_fraction_term(s: str) -> bool:
    s = s.strip()
    if not s or len(s) > 18:
        return False
    if any(c in s for c in [':', ';', ',', '!', '?', '"', "'", '@', '#', '$', '%', '&']):
        return False
    math_words = {'sin', 'cos', 'tan', 'cot', 'sec', 'csc', 'log', 'ln', 'lim', 'exp', 'mod', 'sqrt'}
    words = s.split()
    if len(words) > 4:
        return False
    for w in words:
        w_clean = re.sub(r'[^a-zA-Z]', '', w).lower()
        if len(w_clean) >= 3 and w_clean not in math_words:
            return False
    if not re.search(r'[0-9a-zA-Z\+\-\*]', s):
        return False
    return True

class TestFractionFilter(unittest.TestCase):
    def test_fractions(self):
        self.assertTrue(is_math_fraction_term('5') and is_math_fraction_term('b + 3'))
        self.assertTrue(is_math_fraction_term('2') and is_math_fraction_term('b + 1'))
        self.assertTrue(is_math_fraction_term('3a') and is_math_fraction_term('a - 4'))
        self.assertTrue(is_math_fraction_term('p + r') and is_math_fraction_term('q'))

    def test_prose_dialog_not_fraction(self):
        self.assertFalse(is_math_fraction_term('Report Assistant - Header/Footer'))
        self.assertFalse(is_math_fraction_term('Print cover page'))
        self.assertFalse(is_math_fraction_term('Title: Accounts Payable Report'))
        self.assertFalse(is_math_fraction_term('Comments: Ordered by Supplier Number and Payment Date'))
        self.assertFalse(is_math_fraction_term('Prepared by: S. Holmes'))
        self.assertFalse(is_math_fraction_term('Header:'))
        self.assertFalse(is_math_fraction_term('Date: Upper left'))
        self.assertFalse(is_math_fraction_term('Time: Upper right'))
        self.assertFalse(is_math_fraction_term('Header/Footer Font'))
        self.assertFalse(is_math_fraction_term('Cancel'))
        self.assertFalse(is_math_fraction_term('< Back'))
        self.assertFalse(is_math_fraction_term('Next >'))
        self.assertFalse(is_math_fraction_term('Finish'))

if __name__ == '__main__':
    unittest.main()
