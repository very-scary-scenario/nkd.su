from django.conf import settings

from sly import Lexer
from sly.lex import LexError


class ArtistLexer(Lexer):
    tokens = {
        ARTIST_COMPONENT, SPACE, COMMA, VIA, LPAREN, RPAREN, CV,  # noqa
    }

    VIA = (
        r'\s+('
        r'from|ft\.|feat(\.|uring)?|starring|and|with|&'
        r')\s+'
    )
    LPAREN = r'\s\('
    RPAREN = r'\)(\s|,|$)'
    CV = r'(CV[.:]|[Vv]ocal:|[Mm]ain\svocals?:)\s+'
    COMMA = r',\s+'
    SPACE = r'\s+'
    ARTIST_COMPONENT = (
        r'('
        r'Oranges\sand\sLemons|'
        r'Carole\s&\sTuesday|'
        r'MYTH\s&\sROID|'
        r'[^\s,()]+'
        r')'
    )


artist_lexer = ArtistLexer()


def parse_artist(string, fail_silently=True):
    """
    Generate tuples of (whether or not this is the name of an arist,
    bit of this string), which when combined reform the original string handed
    in.
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
                print(e)
            yield (True, string)
            return
        else:
            raise e

    artist_parts = ('ARTIST_COMPONENT', 'SPACE')

    fragment = None

    for token in tokens:
        is_part_of_artist_name = (token.type in artist_parts)

        if fragment:
            if is_part_of_artist_name == fragment[0]:
                fragment = (fragment[0], fragment[1] + token.value)
                continue

            yield fragment

        fragment = (is_part_of_artist_name, token.value)

    yield fragment


if __name__ == '__main__':
    for string in [
        'Oranges and Lemons',
        'The Very Angry Dolphins',
        'Date Arisa, Yoshimura Haruka, Matsuda Satsumi, Nakatsu Mariko and '
        'Kotobuki Minako',
        'Takagi-san (CV: Takahashi Rie)',
        'Miho and Kana from AIKATSU☆STARS!',
        'Moe, Sunao from STAR☆ANIS',
        'Alicia from BEST FRIENDS!, Remi and Nanase',
    ]:

        print(list(parse_artist(string)))
