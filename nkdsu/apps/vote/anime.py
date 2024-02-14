import hashlib
import os
from itertools import chain
from typing import Literal, Optional
from urllib.parse import urlparse

from django.conf import settings
from pydantic import BaseModel
import requests
from typing_extensions import TypedDict
import ujson

from .utils import camel_to_snake


MAX_ANIME_SUGGESTIONS = 10

ANIME_WEBSITES = {
    'anidb.net': 'AniDB',
    'anilist.co': 'AniList',
    'kitsu.io': 'Kitsu',
    'myanimelist.net': 'MAL',
}

ANIME_PICTURE_DIR = os.path.join(settings.MEDIA_ROOT, 'ap')


class Season(TypedDict):
    year: Optional[int]
    season: Literal['WINTER', 'SPRING', 'SUMMER', 'FALL', 'UNDEFINED']


class Anime(BaseModel):
    title: str
    picture: str
    thumbnail: str
    synonyms: list[str]
    sources: list[str]
    anime_season: Season
    type: Literal['MOVIE', 'ONA', 'OVA', 'SPECIAL', 'TV', 'UNKNOWN']

    def cached_picture_url(self, force_refresh: bool = False) -> str:
        if not os.path.isdir(ANIME_PICTURE_DIR):
            os.makedirs(ANIME_PICTURE_DIR)

        ext = self.picture.split('/')[-1].split('.')[-1]
        filename = f"{hashlib.md5(self.picture.encode()).hexdigest()}.{ext}"
        path = os.path.join(ANIME_PICTURE_DIR, filename)

        if force_refresh or not os.path.exists(path):
            image_content = requests.get(self.picture).content
            with open(path, 'wb') as image_file:
                image_file.write(image_content)

        return f'{settings.MEDIA_URL.rstrip("/")}/ap/{filename}'

    def titles(self) -> list[str]:
        return sorted(chain(self.synonyms, (self.title,)))

    def type_rank(self) -> int:
        """
        Return the priority of a given anime's type. Things that are more
        likely to be included in the nkd.su library will return a lower number.
        """

        return ['TV', 'MOVIE', 'OVA', 'ONA', 'SPECIAL', 'UNKNOWN'].index(self.type)

    def urls(self) -> list[tuple[str, str]]:
        return sorted(
            (
                (website, url)
                for website, url in (
                    (ANIME_WEBSITES.get(urlparse(source).netloc), source)
                    for source in self.sources
                )
                if website is not None
            ),
            key=lambda u: u[0],
        )


by_title: dict[str, Anime] = {}
by_synonym: dict[str, Anime] = {}

with open(
    os.path.join(
        os.path.dirname(__file__),
        'data',
        'mpaod',
        'anime-offline-database.json',
    ),
    'rt',
) as aodf:
    for d in ujson.load(aodf)['data']:
        a = Anime(**{camel_to_snake(k): v for k, v in d.items()})
        if (a.title not in by_title) or (by_title[a.title].type_rank() > a.type_rank()):
            by_title[a.title] = a

        for synonym in a.synonyms:
            if (synonym not in by_synonym) or (
                by_synonym[synonym].type_rank() > a.type_rank()
            ):
                by_synonym[synonym] = a


def get_anime(title: str) -> Optional[Anime]:
    """
    >>> get_anime('Machikado Mazoku').title
    'Machikado Mazoku'
    >>> get_anime('The Demon Girl Next Door').title
    'Machikado Mazoku'
    >>> get_anime('shamiko')
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
        for anime, title in map(lambda t: (get_anime(t), t), Track.all_anime_titles())
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
