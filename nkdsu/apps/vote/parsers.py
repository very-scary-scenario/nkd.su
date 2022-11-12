from dataclasses import dataclass
from typing import Iterable, Optional

from django.conf import settings
from django.urls import reverse

from sly import Lexer
from sly.lex import LexError


@dataclass(frozen=True)
class ArtistChunk:
    text: str
    is_artist: bool

    @property
    def url(self) -> Optional[str]:
        return (
            reverse('vote:artist', kwargs={'artist': self.text})
            if self.is_artist else None
        )

    @property
    def worth_linking_to(self) -> bool:
        from .models import Track

        return bool(
            self.is_artist and
            Track.objects.by_artist(self.text)
        )


@dataclass(frozen=True)
class ParsedArtist:
    chunks: list[ArtistChunk]
    should_collapse: bool

    def __iter__(self) -> Iterable[ArtistChunk]:
        return iter(self.chunks)


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
        r'meets|'
        r'adding|'
        r'a\.k\.a|'
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
        r'\(K\)NoW_NAME|'
        r'AKIMA & NEOS|'
        r'ANNA TSUCHIYA inspi\' NANA\(BLACK STONES\)|'
        r'Bird Bear Hare and Fish|'
        r'Bread & Butter|'
        r'Carole\s&\sTuesday|'
        r'Daisy x Daisy|'
        r'Dejo & Bon|'
        r'Digz, Inc. Group|'
        r'Dimitri From Paris|'
        r'Fear,\sand\sLoathing\sin\sLas\sVegas|'
        r'GENERATIONS from EXILE TRIBE|'
        r'HIGH and MIGHTY COLOR|'
        r'Hello, Happy World!|'
        r'Hifumi,inc\.|'
        r'Kamisama, Boku wa Kizuite shimatta|'
        r'Kevin & Cherry|'
        r'King & Queen|'
        r'Kisida Kyodan & The Akebosi Rockets|'
        r'MYTH\s&\sROID|'
        r'OLIVIA inspi\' REIRA\(TRAPNEST\)|'
        r'Oranges\s(and|&)\sLemons|'
        r'Rough & Ready|'
        r'Run Girls, Run!|'
        r'Simon & Garfunkel|'
        r'THE RAMPAGE from EXILE TRIBE|'
        r'Tackey & Tsubasa|'
        r'Takako & The Crazy Boys|'
        r'Voices From Mars|'
        r'Wake Up, [^\s]+!|'
        r'Yamagami Lucy \(…\)|'
        r'devils and realist|'
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


def chunk_artist(string: str, fail_silently: bool = True) -> Iterable[ArtistChunk]:
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

    fragment: Optional[tuple[bool, str]] = None

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

            yield ArtistChunk(fragment[1], is_artist=fragment[0])

        fragment = (is_part_of_artist_name, token.value)

    if fragment:
        yield ArtistChunk(fragment[1], is_artist=fragment[0])


def parse_artist(string: str, fail_silently: bool = True) -> ParsedArtist:
    if not string:
        return ParsedArtist(chunks=[], should_collapse=False)

    chunks = list(chunk_artist(string, fail_silently=fail_silently))
    naive_is_group = check_for_group(string, chunks[0].text)
    return ParsedArtist(chunks=chunks, should_collapse=naive_is_group and len([
        chunk for chunk in chunks if chunk.is_artist
    ]) > 2)
