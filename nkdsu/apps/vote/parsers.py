from sly import Lexer


class ArtistLexer(Lexer):
    tokens = {
        ARTIST_COMPONENT, SPACE, COMMA, AND, FROM, LPAREN, RPAREN, CV,  # noqa
        FEAT,  # noqa
    }

    FROM = r'\s+from\s+'
    FEAT = r'\s+feat\.\s+'
    LPAREN = r'\('
    RPAREN = r'\)'
    CV = r'CV[.:]\s+'
    COMMA = r',\s+'
    AND = r'\s+and\s+'
    SPACE = r'\s+'
    ARTIST_COMPONENT = (
        r'('
        r'Oranges\sand\sLemons|'
        r'[^\s,()]+'
        r')'
    )


artist_lexer = ArtistLexer()


def parse_artist(string):
    """
    Generate tuples of (whether or not this is the name of an arist,
    bit of this string), which when combined reform the original string handed
    in.
    """

    # look i don't understand how sly works, and i think i might need to spend
    # like a week learning BNF if i want to use its Parser interface, and even
    # then i don't know that it'd help us here, so im just gonna use the lexer
    # and hack the rest of this:

    tokens = list(artist_lexer.tokenize(string))
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
