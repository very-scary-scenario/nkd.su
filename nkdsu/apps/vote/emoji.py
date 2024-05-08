import os
import re
import unicodedata
from typing import Iterable


DIR = os.path.join(os.path.dirname(__file__), 'data', 'emoji')
SEQUENCES_FN = 'emoji-sequences.txt'
ZWJ_SEQUENCES_FN = 'emoji-zwj-sequences.txt'


#: Emoji that should be included in the emoji suggestions dropdown
SUGGESTABLE_EMOJI: dict[str, str] = {}

#: Other emoji; allowed to be used, but not suggested due to there's too many of them
OTHER_ALLOWED_EMOJI: set[str] = set()


def _get_emoji() -> Iterable[str]:
    with open(os.path.join(DIR, SEQUENCES_FN)) as seq_f:
        for line in seq_f.readlines():
            if match := re.match(
                r'^('
                r'(?P<point>[0-9A-F]+)|'
                r'(?P<start>[0-9A-F]+)\.\.(?P<end>[0-9A-F]+)'
                r')\s*;\s*(?P<block>\S+)\s*;.*',
                line,
            ):
                groups = match.groupdict()
                if point := groups.get('point'):
                    yield chr(int(point, base=16))
                else:
                    for kp in range(
                        int(groups['start'], base=16), int(groups['end'], base=16), 1
                    ):
                        yield chr(kp)


for char in _get_emoji():
    try:
        name = unicodedata.name(char)
    except ValueError:
        continue

    SUGGESTABLE_EMOJI[char] = name.lower()


def _get_zwj_sequences() -> Iterable[str]:
    with open(os.path.join(DIR, ZWJ_SEQUENCES_FN)) as seq_f:
        for line in seq_f.readlines():
            if match := re.match(
                r'^' r'(?P<points>[0-9A-F *]+?) *' r';.*$',
                line,
            ):
                groups = match.groupdict()
                yield ''.join(
                    (chr(int(point, 16)) for point in groups['points'].split(' '))
                )


for seq in _get_zwj_sequences():
    OTHER_ALLOWED_EMOJI.add(seq)


if __name__ == '__main__':
    from pprint import pprint

    pprint(SUGGESTABLE_EMOJI)
    pprint(OTHER_ALLOWED_EMOJI)
