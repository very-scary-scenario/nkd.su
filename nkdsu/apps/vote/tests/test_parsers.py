from typing import Optional

from django.test import TestCase

from ..models import Role
from ..parsers import parse_artist


PART_EXAMPLES: list[tuple[str, list[tuple[bool, str]]]] = [
    (
        'Oranges and Lemons',
        [
            (True, 'Oranges and Lemons'),
        ],
    ),
    (
        'The Very Angry Dolphins',
        [
            (True, 'The Very Angry Dolphins'),
        ],
    ),
    (
        'Date Arisa, Yoshimura Haruka, Matsuda Satsumi, Nakatsu Mariko and '
        'Kotobuki Minako',
        [
            (True, 'Date Arisa'),
            (False, ', '),
            (True, 'Yoshimura Haruka'),
            (False, ', '),
            (True, 'Matsuda Satsumi'),
            (False, ', '),
            (True, 'Nakatsu Mariko'),
            (False, ' and '),
            (True, 'Kotobuki Minako'),
        ],
    ),
    (
        'Takagi-san (CV: Takahashi Rie)',
        [
            (True, 'Takagi-san'),
            (False, ' (CV: '),
            (True, 'Takahashi Rie'),
            (False, ')'),
        ],
    ),
    (
        'Miho and Kana from AIKATSU☆STARS!',
        [
            (True, 'Miho'),
            (False, ' and '),
            (True, 'Kana'),
            (False, ' from '),
            (True, 'AIKATSU☆STARS!'),
        ],
    ),
    (
        'Moe, Sunao from STAR☆ANIS',
        [
            (True, 'Moe'),
            (False, ', '),
            (True, 'Sunao'),
            (False, ' from '),
            (True, 'STAR☆ANIS'),
        ],
    ),
    (
        'Alicia from BEST FRIENDS!, Remi and Nanase',
        [
            (True, 'Alicia'),
            (False, ' from '),
            (True, 'BEST FRIENDS!'),
            (False, ', '),
            (True, 'Remi'),
            (False, ' and '),
            (True, 'Nanase'),
        ],
    ),
    (
        'Laala and Mirei (CV: Himika Akaneya and Yu Serizawa from i☆Ris)',
        [
            (True, 'Laala'),
            (False, ' and '),
            (True, 'Mirei'),
            (False, ' (CV: '),
            (True, 'Himika Akaneya'),
            (False, ' and '),
            (True, 'Yu Serizawa'),
            (False, ' from '),
            (True, 'i☆Ris'),
            (False, ')'),
        ],
    ),
    (
        '765PRO&876PRO ALLSTARS',
        [
            (True, '765PRO&876PRO ALLSTARS'),
        ],
    ),
    (
        'Ranka Lee=Nakajima Megumi',
        [
            (True, 'Ranka Lee'),
            (False, '='),
            (True, 'Nakajima Megumi'),
        ],
    ),
    (
        'char = cv',
        [
            (True, 'char'),
            (False, ' = '),
            (True, 'cv'),
        ],
    ),
    (
        'char + cv',
        [
            (True, 'char'),
            (False, ' + '),
            (True, 'cv'),
        ],
    ),
    (
        'Yamagami Lucy (…) (CV: Kayano Ai) Miyoshi Saya (CV: Nakahara Mai)',
        [
            (True, 'Yamagami Lucy (…)'),
            (False, ' (CV: '),
            (True, 'Kayano Ai'),
            (False, ') '),
            (True, 'Miyoshi Saya'),
            (False, ' (CV: '),
            (True, 'Nakahara Mai'),
            (False, ')'),
        ],
    ),
    (
        'Team.Nekokan [Neko] featuring. Amaoto Junca',
        [
            (True, 'Team.Nekokan [Neko]'),
            (False, ' featuring. '),
            (True, 'Amaoto Junca'),
        ],
    ),
    (
        'Lillian Weinberg (Performed by Laura Pitt-Pulford)',
        [
            (True, 'Lillian Weinberg'),
            (False, ' (Performed by '),
            (True, 'Laura Pitt-Pulford'),
            (False, ')'),
        ],
    ),
    (
        'SawanoHiroyuki[nZk]:collab',
        [
            (True, 'SawanoHiroyuki[nZk]'),
            (False, ':'),
            (True, 'collab'),
        ],
    ),
    (
        'SawanoHiroyuki[nZk]:Tielle&Gemie',
        [
            (True, 'SawanoHiroyuki[nZk]'),
            (False, ':'),
            (True, 'Tielle'),
            (False, '&'),
            (True, 'Gemie'),
        ],
    ),
    (
        'SawanoHiroyuki[nZk]:someone:else',
        [
            (True, 'SawanoHiroyuki[nZk]'),
            (False, ':'),
            (True, 'someone:else'),
        ],
    ),
    (
        'SawanoHiroyuki[nZk]:someone&someone:else&yet another person',
        [
            (True, 'SawanoHiroyuki[nZk]'),
            (False, ':'),
            (True, 'someone'),
            (False, '&'),
            (True, 'someone:else'),
            (False, '&'),
            (True, 'yet another person'),
        ],
    ),
    (
        'SawanoHiroyuki[nzk]:collab',
        [
            (True, 'SawanoHiroyuki[nzk]:collab'),
        ],
    ),
    (
        'FLOWxGRANRODEO',
        [
            (True, 'FLOW'),
            (False, 'x'),
            (True, 'GRANRODEO'),
        ],
    ),
    (
        'FLOWxGRANDRODEO',
        [
            (True, 'FLOWxGRANDRODEO'),
        ],
    ),
    (
        'fu_mou (Hifumi,inc.)',
        [
            (True, 'fu_mou'),
            (False, ' ('),
            (True, 'Hifumi,inc.'),
            (False, ')'),
        ],
    ),
    (
        'Morinaka Kazaki meets ▽▲TRiNITY▲▽',
        [
            (True, 'Morinaka Kazaki'),
            (False, ' meets '),
            (True, '▽▲TRiNITY▲▽'),
        ],
    ),
]

GROUP_EXAMPLES = [
    ('This is a group (but it only has one paren section)', False),
    ('This is a group (the parens (are nested) (but do not end) until the end)', True),
    ('This is not a group; there are no parens', False),
    ('This is not a group (there are parens here) but not here', False),
    ('This is not a group (the parens) (do not reach to the end)', False),
    ('This is not a group (the parens (open too many times)', False),
]


class ArtistParserTests(TestCase):
    def test_artist_parts(self) -> None:
        for string, expected_result in PART_EXAMPLES:
            self.assertEqual(
                [(a.is_artist, a.text) for a in parse_artist(string).chunks],
                expected_result,
            )

    def test_group_detection(self) -> None:
        for string, first_part_should_be_group in GROUP_EXAMPLES:
            parsed = parse_artist(string)

            if first_part_should_be_group:
                self.assertTrue(parsed.should_collapse, msg=string)
            else:
                self.assertFalse(parsed.should_collapse, msg=string)


ROLE_EXAMPLES: dict[str, tuple[Optional[str], Optional[str], str, str, str]] = {
    '': (None, None, '', '', ''),
    'unmatchable': ('unmatchable', None, '', '', ''),
    'Mobile Suit Gundam SEED ED3': ('Mobile Suit Gundam SEED', None, 'ED', '3', 'ED3'),
    "Vivy -Fluorite Eye's Song- Character Song": (
        "Vivy -Fluorite Eye's Song-",
        None,
        'Character Song',
        '',
        'Character Song',
    ),
    'Pop Team Epic Rebroadcast OP': ('Pop Team Epic', 'Rebroadcast ', 'OP', '', 'OP'),
    'takt op.Destiny ED': ('takt op.Destiny', None, 'ED', '', 'ED'),
    'Im OP Even at lv1 OP': ('Im OP Even at lv1', None, 'OP', '', 'OP'),
    'Im OP Even at lv1 OP 1': ('Im OP Even at lv1', None, 'OP', '1', 'OP 1'),
    'twgok ED EP07': ('twgok', None, 'ED', 'EP07', 'ED EP07'),
    'idfs ED EP01-03': ('idfs', None, 'ED', 'EP01-03', 'ED EP01-03'),
    'idfs insert song EP01-03': (
        'idfs',
        None,
        'insert song',
        'EP01-03',
        'insert song EP01-03',
    ),
}


class RoleParserTests(TestCase):
    def test_role_parsing(self) -> None:
        for full_tag, expected_result in ROLE_EXAMPLES.items():
            role = Role(full_tag)
            self.assertEqual(
                (
                    role.anime,
                    role.caveat,
                    role.kind,
                    role.specifics,
                    role.full_role,
                ),
                expected_result,
            )
