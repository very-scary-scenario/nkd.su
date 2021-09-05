from dataclasses import dataclass, field
from typing import Iterable, Optional, Tuple

from django.conf import settings

from sly import Lexer
from sly.lex import LexError


@dataclass
class ArtistChunk:
    text: str
    is_artist: bool
    is_group: bool = field(default=False)


class ArtistLexer(Lexer):
    tokens = {
        SPECIAL_CASE, ARTIST_COMPONENT, SPACE, COMMA, VIA, LPAREN, RPAREN, CV,  # type: ignore  # noqa
    }

    SPECIAL_CASE = (
        r'^('
        r'FLOWxGRANRODEO|'
        r'SawanoHiroyuki\[nZk\]:.*'
        r')$'
    )
    VIA = (
        r'\s+('
        r'from|'
        r'ft\.|'
        r'feat(\.|uring)?\.?|'
        r'[Ss]tarring|'
        r'and|'
        r'with|'
        r'adding|'
        r'x|'
        r'×|'
        r'n\'|'
        r'vs\.?|'
        r'/|'
        r'\+|'
        r'&'
        r')\s+'
    )
    LPAREN = r'(?<=\s)\('
    RPAREN = r'\)(?=\s|,|\)|$)'
    CV = (
        r'('
        r'CV[.:]|'
        r'[Vv]ocals?:|'
        r'[Mm]ain\svocals?:|'
        r'[Cc]omposed\sby|'
        r'[Ff]rom|'
        r'[Ff]eat(\.|uring)?|'
        r'[Pp]erformed\sby|'
        r'Vo\.'
        r')\s+|='
    )
    COMMA = r',(\sand)?\s+'
    SPACE = r'\s+'
    ARTIST_COMPONENT = (
        r'('
        r'AKIMA & NEOS|'
        r'ANNA TSUCHIYA inspi\' NANA\(BLACK STONES\)|'
        r'Bird Bear Hare and Fish|'
        r'Bread & Butter|'
        r'Carole\s&\sTuesday|'
        r'Daisy x Daisy|'
        r'Dejo & Bon|'
        r'Dimitri From Paris|'
        r'Fear,\sand\sLoathing\sin\sLas\sVegas|'
        r'GENERATIONS from EXILE TRIBE|'
        r'HIGH and MIGHTY COLOR|'
        r'Hello, Happy World!|'
        r'Kamisama, Boku wa Kizuite shimatta|'
        r'Kevin & Cherry|'
        r'King & Queen|'
        r'Kisida Kyodan & The Akebosi Rockets|'
        r'MYTH\s&\sROID|'
        r'OLIVIA inspi\' REIRA\(TRAPNEST\)|'
        r'Oranges\sand\sLemons|'
        r'Rough & Ready|'
        r'Run Girls, Run!|'
        r'Simon & Garfunkel|'
        r'Takako & The Crazy Boys|'
        r'THE RAMPAGE from EXILE TRIBE|'
        r'Tackey & Tsubasa|'
        r'Voices From Mars|'
        r'Wake Up, [^\s]+!|'
        r'＊\(Asterisk\)|'
        r'[^\s=,()]+'
        r')'
    )


artist_lexer = ArtistLexer()


def handle_special_case(token) -> Iterable[ArtistChunk]:
    if token.value == "FLOWxGRANRODEO":
        yield ArtistChunk('FLOW', is_artist=True)
        yield ArtistChunk('x', is_artist=False)
        yield ArtistChunk('GRANRODEO', is_artist=True)
    elif token.value.startswith('SawanoHiroyuki[nZk]:'):
        sawano, collaborators = token.value.split(':', 1)
        yield ArtistChunk(sawano, is_artist=True)
        yield ArtistChunk(':', is_artist=False)
        for i, collaborator in enumerate(collaborators.split('&')):
            if i != 0:
                yield ArtistChunk('&', is_artist=False)
            yield ArtistChunk(collaborator, is_artist=True)

    else:
        raise NotImplementedError(token.value)


def check_for_group(full_string: str, maybe_group_name: str) -> bool:
    remainder = full_string.replace(maybe_group_name, '', 1)
    if not remainder.startswith(' ('):
        return False

    paren_count = 0

    for i, char in enumerate(remainder):
        if char == '(':
            paren_count += 1
        elif char == ')':
            paren_count -= 1

        if (paren_count == 0) and (i > 0) and (i < (len(remainder) - 1)):
            return False

    return paren_count == 0


def parse_artist(string: str, fail_silently: bool = True) -> Iterable[ArtistChunk]:
    """
    Return a bunch of `ArtistChunk`s which, when combined, reform the string
    handed in.
    """

    # look i don't understand how sly works, and i think i might need to spend
    # like a week learning BNF if i want to use its Parser interface, and even
    # then i don't know that it'd help us here, so im just gonna use the lexer
    # and hack the rest of this:

    try:
        tokens = list(artist_lexer.tokenize(string))
    except LexError as e:
        if fail_silently:
            if settings.DEBUG:
                print(f'problem parsing artist name {string!r}:\n  {e}')
            yield ArtistChunk(text=string, is_artist=True)
            return
        else:
            raise e

    artist_parts = ('ARTIST_COMPONENT', 'SPACE')

    fragment: Optional[Tuple[bool, str]] = None
    we_have_yielded = False

    for ti, token in enumerate(tokens):
        if token.type == 'SPECIAL_CASE':
            yield from handle_special_case(token)
            continue

        is_part_of_artist_name = (
            (token.type in artist_parts) and
            (
                (token.type != 'SPACE') or
                (
                    # if this is a space, then:
                    (
                        # be false if the next token isn't an artist component
                        (ti+1 < len(tokens)) and
                        (tokens[ti+1].type == 'ARTIST_COMPONENT')
                    ) and (
                        # or if the previous one wasn't, either
                        (ti > 0) and
                        (tokens[ti-1].type == 'ARTIST_COMPONENT')
                    )
                )
            )
        )

        if fragment:
            if is_part_of_artist_name == fragment[0]:
                fragment = (fragment[0], fragment[1] + token.value)
                continue

            if fragment[0] and not we_have_yielded:
                is_group = check_for_group(string, fragment[1])
            else:
                is_group = False

            yield ArtistChunk(fragment[1], is_artist=fragment[0], is_group=is_group)

            we_have_yielded = True

        fragment = (is_part_of_artist_name, token.value)

    if fragment:
        yield ArtistChunk(fragment[1], is_artist=fragment[0])
