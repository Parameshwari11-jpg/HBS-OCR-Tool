import sys
import unittest
sys.path.insert(0, r'c:\Users\HBS\Desktop\OCR\backend')

from app.utils.spacing_engine import merge_tokens, should_insert_space

class TestSpacingEngine(unittest.TestCase):

    def test_two_normal_words(self):
        # Generic arbitrary pairs of standalone words
        self.assertEqual(merge_tokens(['Contributing', 'Writers']), 'Contributing Writers')
        self.assertEqual(merge_tokens(['Executive', 'Director']), 'Executive Director')
        self.assertEqual(merge_tokens(['hello', 'world']), 'hello world')
        self.assertEqual(merge_tokens(['sample', 'document']), 'sample document')

    def test_multiple_words_and_sentences(self):
        sentence_frags = ['The', 'quick', 'brown', 'fox', 'jumps', 'over', 'the', 'lazy', 'dog', '.']
        self.assertEqual(merge_tokens(sentence_frags), 'The quick brown fox jumps over the lazy dog.')

        multi_frags = ['Multi', 'node', 'text', 'extraction', 'works', 'correctly']
        self.assertEqual(merge_tokens(multi_frags), 'Multi node text extraction works correctly')

    def test_punctuation_attachment(self):
        self.assertEqual(merge_tokens(['word', ',']), 'word,')
        self.assertEqual(merge_tokens(['word', '.']), 'word.')
        self.assertEqual(merge_tokens(['word', ';']), 'word;')
        self.assertEqual(merge_tokens(['word', ':']), 'word:')
        self.assertEqual(merge_tokens(['word', '!']), 'word!')
        self.assertEqual(merge_tokens(['word', '?']), 'word?')

    def test_brackets_and_quotes(self):
        self.assertEqual(merge_tokens(['(', 'word']), '(word')
        self.assertEqual(merge_tokens(['word', ')']), 'word)')
        self.assertEqual(merge_tokens(['[', 'item']), '[item')
        self.assertEqual(merge_tokens(['item', ']']), 'item]')

    def test_apostrophes_and_contractions(self):
        self.assertEqual(merge_tokens(['word', "'s"]), "word's")
        self.assertEqual(merge_tokens(['don', "'t"]), "don't")
        self.assertEqual(merge_tokens(['it', "'s"]), "it's")

    def test_hyphenated_words(self):
        self.assertEqual(merge_tokens(['semi-', 'annual']), 'semi-annual')
        self.assertEqual(merge_tokens(['well', '-known']), 'well-known')
        self.assertEqual(merge_tokens(['state-', 'of', '-the', '-art']), 'state-of-the-art')

    def test_numbers_and_units(self):
        self.assertEqual(merge_tokens(['Chapter', '5']), 'Chapter 5')
        self.assertEqual(merge_tokens(['Section', '12']), 'Section 12')
        self.assertEqual(merge_tokens(['100', 'meters']), '100 meters')
        self.assertEqual(merge_tokens(['25', 'books']), '25 books')
        # Units and suffixes
        self.assertEqual(merge_tokens(['100', 'px']), '100px')
        self.assertEqual(merge_tokens(['5', 'kg']), '5kg')
        self.assertEqual(merge_tokens(['10', 'th']), '10th')
        self.assertEqual(merge_tokens(['1', 'st']), '1st')
        self.assertEqual(merge_tokens(['3.', '14']), '3.14')

    def test_dates_and_acronyms(self):
        self.assertEqual(merge_tokens(['October', '7']), 'October 7')
        self.assertEqual(merge_tokens(['U.', 'S.', 'A.']), 'U.S.A.')

    def test_proper_nouns_and_caps(self):
        self.assertEqual(merge_tokens(['New', 'York']), 'New York')
        self.assertEqual(merge_tokens(['UNITED', 'STATES']), 'UNITED STATES')
        self.assertEqual(merge_tokens(['SECTION', 'FIVE']), 'SECTION FIVE')

    def test_compound_words_and_prefixes(self):
        self.assertEqual(merge_tokens(['super', 'script']), 'superscript')
        self.assertEqual(merge_tokens(['inter', 'national']), 'international')
        self.assertEqual(merge_tokens(['every', 'body']), 'everybody')
        self.assertEqual(merge_tokens(['life', 'style']), 'lifestyle')
        self.assertEqual(merge_tokens(['some', 'thing']), 'something')
        self.assertEqual(merge_tokens(['pre', 'requisite']), 'prerequisite')

    def test_preserved_whitespace(self):
        self.assertEqual(merge_tokens(['Existing ', 'space']), 'Existing space')
        self.assertEqual(merge_tokens(['Existing', ' space']), 'Existing space')
        self.assertEqual(merge_tokens(['Line\n', 'break']), 'Line\nbreak')

    def test_layout_coordinate_hints(self):
        # Physical space exists: coord_gap=3.0, font_size=10.0 -> ratio=0.30 -> space
        self.assertEqual(merge_tokens(['Custom', 'Font'], coord_gaps=[3.0], font_sizes=[10.0]), 'Custom Font')
        # Touching letters: coord_gap=0.1, font_size=10.0 -> ratio=0.01
        self.assertEqual(merge_tokens(['super', 'script'], coord_gaps=[0.1], font_sizes=[10.0]), 'superscript')

if __name__ == '__main__':
    unittest.main()
