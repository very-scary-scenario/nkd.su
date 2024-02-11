import os
from itertools import chain
from typing import Literal, Optional

from pydantic import BaseModel
from typing_extensions import TypedDict
import ujson

from .utils import camel_to_snake


MAX_ANIME_SUGGESTIONS = 10


class Season(TypedDict):
    year: Optional[int]
    season: Literal['SPRING', 'SUMMER', 'FALL', 'WINTER', 'UNDEFINED']


class Anime(BaseModel):
    title: str
    synonyms: list[str]
    sources: list[str]
    anime_season: Season
    type: Literal['MOVIE', 'ONA', 'OVA', 'TV', 'UNKNOWN']

    def titles(self) -> list[str]:
        return sorted(chain(self.synonyms, (self.title,)))


with open(
    os.path.join(
        os.path.dirname(__file__),
        'data',
        'mpaod',
        'anime-offline-database.json',
    ),
    'rt',
) as aodf:
    by_title = {
        a['title']: Anime(**{camel_to_snake(k): v for k, v in a.items()})
        for a in ujson.load(aodf)['data']
        if a['type'] != 'SPECIAL'
    }


by_synonym = {
    synonym: anime for anime in by_title.values() for synonym in anime.synonyms
}


def anime(title: str) -> Optional[Anime]:
    """
    >>> anime('Machikado Mazoku').title
    'Machikado Mazoku'
    >>> anime('The Demon Girl Next Door').title
    'Machikado Mazoku'
    >>> anime('shamiko')
    """

    return by_title.get(title) or by_synonym.get(title)


def fuzzy_nkdsu_aliases() -> dict[str, str]:
    """
    Return a dict of ``{alias: nkdsu_title}`` where ``nkdsu_title`` is an anime
    included in the nkd.su database, and ``alias`` is a lowercased alternative
    title for the ``nkdsu_title`` it points to.

    >>> from pprint import pprint
    >>> from nkdsu.apps.vote.models import Track
    >>> from django.utils.timezone import now
    >>> defaults = dict(
    ...     id3_artist='someone', hidden=False, inudesu=False, added=now(), revealed=now()
    ... )

    With some anime titles that don't have very many synonyms:

    >>> Track.objects.create(**defaults, id='1', id3_title='song (Eiji OP1)')
    <Track: ‘song’ (Eiji OP1) - someone>
    >>> Track.objects.create(**defaults, id='2', id3_title='ditty (◯ ED1)')
    <Track: ‘ditty’ (◯ ED1) - someone>
    >>> pprint(fuzzy_nkdsu_aliases())
    {'"eiji"': 'Eiji',
     'circle': '◯',
     'eiji': 'Eiji',
     'o (sawako kabuki)': '◯',
     '°': '◯',
     '○': '◯',
     '◯': '◯',
     '「エイジ」': 'Eiji',
     'エイジ': 'Eiji'}
    """

    from .models import Track

    return {
        alt_title.lower(): title
        for anime, title in map(lambda t: (anime(t), t), Track.all_anime_titles())
        if anime is not None
        for alt_title in anime.titles()
    }


def suggest_anime(query: str) -> set[str]:
    lower_query = query.lower()
    suggestions: set[str] = set()

    for alias, canonical_title in fuzzy_nkdsu_aliases().items():
        if lower_query in alias:
            suggestions.add(canonical_title)

            if len(suggestions) > MAX_ANIME_SUGGESTIONS:
                return set()

    return suggestions
