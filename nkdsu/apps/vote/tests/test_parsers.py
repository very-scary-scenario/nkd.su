from ..parsers import parse_artist


from django.test import TestCase


ARTIST_EXAMPLES = [
    ('Oranges and Lemons', [
        (True, 'Oranges and Lemons'),
    ]),
    ('The Very Angry Dolphins', [
        (True, 'The Very Angry Dolphins'),
    ]),
    ('Date Arisa, Yoshimura Haruka, Matsuda Satsumi, Nakatsu Mariko and '
     'Kotobuki Minako', [
         (True, 'Date Arisa'),
         (False, ', '),
         (True, 'Yoshimura Haruka'),
         (False, ', '),
         (True, 'Matsuda Satsumi'),
         (False, ', '),
         (True, 'Nakatsu Mariko'),
         (False, ' and '),
         (True, 'Kotobuki Minako'),
     ]),
    ('Takagi-san (CV: Takahashi Rie)', [
        (True, 'Takagi-san'),
        (False, ' (CV: '),
        (True, 'Takahashi Rie'),
        (False, ')'),
    ]),
    ('Miho and Kana from AIKATSU☆STARS!', [
        (True, 'Miho'),
        (False, ' and '),
        (True, 'Kana'),
        (False, ' from '),
        (True, 'AIKATSU☆STARS!'),
    ]),
    ('Moe, Sunao from STAR☆ANIS', [
        (True, 'Moe'),
        (False, ', '),
        (True, 'Sunao'),
        (False, ' from '),
        (True, 'STAR☆ANIS'),
    ]),
    ('Alicia from BEST FRIENDS!, Remi and Nanase', [
        (True, 'Alicia'),
        (False, ' from '),
        (True, 'BEST FRIENDS!'),
        (False, ', '),
        (True, 'Remi'),
        (False, ' and '),
        (True, 'Nanase')
    ]),
    ('Laala and Mirei (CV: Himika Akaneya and Yu Serizawa from i☆Ris)', [
        (True, 'Laala'),
        (False, ' and '),
        (True, 'Mirei'),
        (False, ' (CV: '),
        (True, 'Himika Akaneya'),
        (False, ' and '),
        (True, 'Yu Serizawa'),
        (False, ' from '),
        (True, 'i☆Ris'),
        (False, ')')
    ]),
    ('765PRO&876PRO ALLSTARS', [
        (True, '765PRO&876PRO ALLSTARS'),
    ]),
]


class ArtistParserTests(TestCase):
    def test_examples(self):
        for string, expected_result in ARTIST_EXAMPLES:
            self.assertEqual(list(parse_artist(string)),  expected_result)
