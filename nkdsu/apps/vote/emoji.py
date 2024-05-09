import os
import re
from itertools import chain
from typing import Iterable

import unicodedata2 as unicodedata


DIR = os.path.join(os.path.dirname(__file__), 'data', 'emoji')
SEQUENCES_FN = 'emoji-sequences.txt'
ZWJ_SEQUENCES_FN = 'emoji-zwj-sequences.txt'


#: Emoji that should be included in the emoji suggestions dropdown
SUGGESTABLE_EMOJI: dict[str, str] = {}

#: Other emoji; allowed to be used, but not suggested due to there's too many of them
OTHER_ALLOWED_EMOJI: dict[str, str] = {}


GROUP_HOMES = {
    'Basic_Emoji': SUGGESTABLE_EMOJI,
    'Emoji_Keycap_Sequence': SUGGESTABLE_EMOJI,
    'RGI_Emoji_Flag_Sequence': SUGGESTABLE_EMOJI,
    'RGI_Emoji_Tag_Sequence': SUGGESTABLE_EMOJI,
    'RGI_Emoji_Modifier_Sequence': OTHER_ALLOWED_EMOJI,
    'Family': OTHER_ALLOWED_EMOJI,
    'Role': OTHER_ALLOWED_EMOJI,
    'Gendered': OTHER_ALLOWED_EMOJI,
    'Hair': OTHER_ALLOWED_EMOJI,
    'Other': SUGGESTABLE_EMOJI,
}


def _get_emoji() -> Iterable[tuple[str, str, str]]:
    with open(os.path.join(DIR, SEQUENCES_FN)) as seq_f:
        for line in seq_f.readlines():
            if match := re.match(
                r'^('
                r'(?P<points>[0-9A-F ]+?)|'
                r'(?P<start>[0-9A-F]+)\.\.(?P<end>[0-9A-F]+)'
                r')\s*;\s*(?P<block>\S+)\s*; *(?P<name>.+?) *#.*$',
                line,
            ):
                groups = match.groupdict()
                if points := groups.get('points'):
                    yield groups['block'], ''.join(
                        chr(int(point, base=16)) for point in points.split(' ')
                    ), groups['name']
                else:
                    for kp in range(
                        int(groups['start'], base=16), int(groups['end'], base=16), 1
                    ):
                        char = chr(kp)
                        yield groups['block'], char, unicodedata.name(char).lower()


def _get_zwj_sequences() -> Iterable[tuple[str, str, str]]:
    with open(os.path.join(DIR, ZWJ_SEQUENCES_FN)) as seq_f:
        group = ''
        for line in seq_f.readlines():
            if match := re.match(r'^# RGI_Emoji_ZWJ_Sequence: (?P<group>.*)$', line):
                group = match.groupdict()['group']
                continue

            if match := re.match(
                r'^' r'(?P<points>[0-9A-F *]+?) *' r';.*; *(?P<description>.+?) *#.*$',
                line,
            ):
                groups = match.groupdict()
                yield (
                    group,
                    ''.join(
                        (chr(int(point, 16)) for point in groups['points'].split(' '))
                    ),
                    groups['description'],
                )


for group, char, name in chain(_get_emoji(), _get_zwj_sequences()):
    if name.startswith('emoji '):
        # don't suggest modifiers (eg. lone hair or skin tone indicators)
        OTHER_ALLOWED_EMOJI[char] = name
    else:
        GROUP_HOMES[group][char] = name


# some checks that we've read stuff correctly:
assert SUGGESTABLE_EMOJI['⭐'] == 'star'
assert SUGGESTABLE_EMOJI['🐕‍🦺'] == 'service dog'
assert OTHER_ALLOWED_EMOJI['🧑🏿‍🦳'] == 'person: dark skin tone, white hair'
assert OTHER_ALLOWED_EMOJI['🦳'] == 'emoji component white hair'


if __name__ == '__main__':
    from pprint import pprint

    pprint(SUGGESTABLE_EMOJI)
    pprint(OTHER_ALLOWED_EMOJI)
