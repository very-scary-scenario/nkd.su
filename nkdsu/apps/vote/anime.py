import os
from itertools import chain
from typing import Literal, Optional

from pydantic import BaseModel
from typing_extensions import TypedDict
import ujson

from .utils import camel_to_snake


class Season(TypedDict):
    year: Optional[int]
    season: Literal['SPRING', 'SUMMER', 'FALL', 'WINTER', 'UNDEFINED']


class Anime(BaseModel):
    title: str
    synonyms: list[str]
    sources: list[str]
    anime_season: Season

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
