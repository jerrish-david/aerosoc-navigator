import re
import unittest

from kjv_source import (
    BOOK_ALIASES,
    DEFAULT_OUTPUT,
    book_key,
    load_index,
    message_length,
    parse_reference,
    render_reference,
)


class ReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = load_index(DEFAULT_OUTPUT)

    def assert_passage(self, result, expected):
        recovered = {}
        total = len(result['messages'])
        for number, message in enumerate(result['messages'], 1):
            header, body = message.split('\n\n', 1)
            self.assertEqual(header, f'📖 {result["reference"]} — KJV [{number}/{total}]')
            self.assertLessEqual(message_length(message), result['limit'])
            self.assertEqual(message_length(message), result['lengths'][number - 1])
            for paragraph in body.split('\n\n'):
                match = re.fullmatch(r'([0-9]+):([0-9]+) (.*)', paragraph, re.DOTALL)
                self.assertIsNotNone(match)
                verse = match[2]
                recovered[verse] = recovered.get(verse, '') + match[3]
        self.assertEqual(recovered, expected)
        self.assertEqual(list(recovered), list(expected))

    def test_user_example(self):
        result = render_reference(self.index, '1 cor 6 7-10')
        self.assertEqual(result['reference'], '1 Corinthians 6:7-10')
        self.assertEqual(len(result['messages']), 2)
        entry = self.index['chapters']['1 corinthians:6']['verses']
        self.assertEqual(result['messages'], [
            f'📖 1 Corinthians 6:7-10 — KJV [1/2]\n\n6:7 {entry["7"]}'
            f'\n\n6:8 {entry["8"]}\n\n6:9 {entry["9"]}',
            f'📖 1 Corinthians 6:7-10 — KJV [2/2]\n\n6:10 {entry["10"]}',
        ])

    def test_supported_spellings(self):
        for reference in ('1 cor 6 7-10', '1Cor.6:7-10', ' 1 COR 6:7 – 10 ',
                          '1 Corinthians 6:7—10', '1_Corinthians 6:7-10'):
            with self.subTest(reference=reference):
                self.assertEqual(parse_reference(reference), ('1 Corinthians', 6, 7, 10))
        self.assertEqual(parse_reference('psalms 23 1'), ('Psalm', 23, 1, 1))

    def test_aliases_cover_index(self):
        books = {entry['book'] for entry in self.index['chapters'].values()}
        self.assertEqual(set(BOOK_ALIASES.values()), books)
        for alias, canonical in BOOK_ALIASES.items():
            self.assertEqual(parse_reference(f'{alias} 1:1')[0], canonical)

    def test_bad_references(self):
        for reference in ('1 cor 6 10-7', 'cor 6 7', 'j 1 1', 'John 0:1',
                          'John 1:0', 'John 999:1', 'John 3:999', 'John 3:1-999999999',
                          'John 3:16-4:2', 'John 3:16; Rom 1:1', 'John 3:16 garbage'):
            with self.subTest(reference=reference), self.assertRaises(ValueError):
                render_reference(self.index, reference)

    def test_all_chapters_preserve_text_and_limits(self):
        for entry in self.index['chapters'].values():
            verses = entry['verses']
            reference = f'{entry["book"]} {entry["chapter"]}:1-{len(verses)}'
            with self.subTest(reference=reference):
                self.assert_passage(render_reference(self.index, reference), verses)

    def test_long_verse(self):
        result = render_reference(self.index, 'Esther 8:9')
        self.assertGreater(len(result['messages']), 1)
        self.assert_passage(result, {'9': self.index['chapters']['esther:8']['verses']['9']})

    def test_page_count_digit_boundaries(self):
        verses = {str(number): 'words ' * 12 for number in range(1, 106)}
        index = {'chapters': {'john:1': {'book': 'John', 'verses': verses}}}
        for end in (9, 10, 99, 100, 105):
            with self.subTest(end=end):
                result = render_reference(index, f'John 1:1-{end}', limit=125)
                self.assertEqual(len(result['messages']), end)
                self.assert_passage(result, {str(number): verses[str(number)]
                                             for number in range(1, end + 1)})

    def test_unicode_and_tiny_limits(self):
        self.assertEqual(message_length('📖'), 2)
        verses = {'1': '📖' * 400 + ' more words'}
        index = {'chapters': {f'{book_key("John")}:1': {'book': 'John', 'verses': verses}}}
        result = render_reference(index, 'John 1:1', limit=100)
        self.assert_passage(result, verses)
        for limit in (0, -1, 1, 10, 1.5, True):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                render_reference(index, 'John 1:1', limit=limit)


if __name__ == '__main__':
    unittest.main()
