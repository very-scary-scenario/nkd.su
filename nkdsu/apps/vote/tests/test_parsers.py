from django.test import TestCase

from ..parsers import parse_artist


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
    ('Ranka Lee=Nakajima Megumi', [
        (True, 'Ranka Lee'),
        (False, '='),
        (True, 'Nakajima Megumi'),
    ]),
    ('char = cv', [
        (True, 'char'),
        (False, ' = '),
        (True, 'cv'),
    ]),
    ('char + cv', [
        (True, 'char'),
        (False, ' + '),
        (True, 'cv'),
    ]),
    ('Team.Nekokan [Neko] featuring. Amaoto Junca', [
        (True, 'Team.Nekokan [Neko]'),
        (False, ' featuring. '),
        (True, 'Amaoto Junca'),
    ]),
    ('Lillian Weinberg (Performed by Laura Pitt-Pulford)', [
        (True, 'Lillian Weinberg'),
        (False, ' (Performed by '),
        (True, 'Laura Pitt-Pulford'),
        (False, ')'),
    ]),
    ('SawanoHiroyuki[nZk]:collab', [
        (True, 'SawanoHiroyuki[nZk]'),
        (False, ':'),
        (True, 'collab'),
    ]),
    ('SawanoHiroyuki[nZk]:Tielle&Gemie', [
        (True, 'SawanoHiroyuki[nZk]'),
        (False, ':'),
        (True, 'Tielle'),
        (False, '&'),
        (True, 'Gemie'),
    ]),
    ('SawanoHiroyuki[nZk]:someone:else', [
        (True, 'SawanoHiroyuki[nZk]'),
        (False, ':'),
        (True, 'someone:else'),
    ]),
    ('SawanoHiroyuki[nZk]:someone&someone:else&yet another person', [
        (True, 'SawanoHiroyuki[nZk]'),
        (False, ':'),
        (True, 'someone'),
        (False, '&'),
        (True, 'someone:else'),
        (False, '&'),
        (True, 'yet another person'),
    ]),
    ('SawanoHiroyuki[nzk]:collab', [
        (True, 'SawanoHiroyuki[nzk]:collab'),
    ]),
    ('FLOWxGRANRODEO', [
        (True, 'FLOW'),
        (False, 'x'),
        (True, 'GRANRODEO'),
    ]),
    ('FLOWxGRANDRODEO', [
        (True, 'FLOWxGRANDRODEO'),
    ]),
]


class ArtistParserTests(TestCase):
    def test_examples(self) -> None:
        for string, expected_result in ARTIST_EXAMPLES:
            self.assertEqual([
                (a.is_artist, a.text) for a in parse_artist(string)
            ],  expected_result)
