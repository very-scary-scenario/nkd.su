from typing import Literal, Optional
import os

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
