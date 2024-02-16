from __future__ import annotations

import hashlib
import os
from itertools import chain
from typing import Literal, Optional

from django.conf import settings
from pydantic import BaseModel, HttpUrl
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
    picture: HttpUrl
    thumbnail: HttpUrl
    synonyms: list[str]
    sources: list[HttpUrl]
    relations: list[HttpUrl]
    anime_season: Season
    type: Literal['MOVIE', 'ONA', 'OVA', 'SPECIAL', 'TV', 'UNKNOWN']

    @property
    def quarter(self) -> str:
        quarter = {
            'WINTER': 'q1',
            'SPRING': 'q2',
            'SUMMER': 'q3',
            'FALL': 'q4',
            'UNDEFINED': 'q?',
        }[self.anime_season['season']]
        return f'{self.anime_season["year"]}-{quarter}'

    def cached_picture_filename(self) -> str:
        if not os.path.isdir(ANIME_PICTURE_DIR):
            os.makedirs(ANIME_PICTURE_DIR)

        path = self.picture.path
        assert path is not None, f"{self.picture} has no path"
        ext = path.split('/')[-1].split('.')[-1]
        return f"{hashlib.md5(str(self.picture).encode()).hexdigest()}.{ext}"

    def cached_picture_path(self) -> str:
        return os.path.join(ANIME_PICTURE_DIR, self.cached_picture_filename())

    def picture_is_cached(self) -> bool:
        return os.path.exists(self.cached_picture_path())

    def cached_picture_url(self, force_refresh: bool = False) -> str:
        return f'{settings.MEDIA_URL.rstrip("/")}/ap/{self.cached_picture_filename()}'

    def cache_picture(self) -> None:
        image_content = requests.get(str(self.picture)).content
        with open(self.cached_picture_path(), 'wb') as image_file:
            image_file.write(image_content)

    def titles(self) -> list[str]:
        return sorted(chain(self.synonyms, (self.title,)))

    def type_rank(self) -> int:
        """
        Return the priority of a given anime's type. Things that are more
        likely to be included in the nkd.su library will return a lower number.
        """

        return ['TV', 'MOVIE', 'OVA', 'ONA', 'SPECIAL', 'UNKNOWN'].index(self.type)

    def urls(self) -> list[tuple[str, HttpUrl]]:
        return sorted(
            (
                (website, url)
                for website, url in (
                    (ANIME_WEBSITES.get(source.host), source)
                    for source in self.sources
                    if source.host is not None
                )
                if website is not None
            ),
            key=lambda u: u[0],
        )

    def related_anime(self) -> list[str]:
        from .models import Track

        return [
            title
            for title, anime in sorted(
                (
                    (title, anime)
                    for title, anime in (
                        (anime_title, get_anime(anime_title))
                        for anime_title in Track.all_anime_titles()
                    )
                    if anime is not None
                    and any((source in self.relations for source in anime.sources))
                ),
                key=lambda ta: ta[1].quarter,
            )
        ]


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
