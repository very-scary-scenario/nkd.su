from typing import Literal, Optional
import os

from pydantic import BaseModel
from typing_extensions import TypedDict
import ujson


class Season(TypedDict):
    year: Optional[int]
    season: Literal['SPRING', 'SUMMER', 'FALL', 'WINTER', 'UNDEFINED']


class Anime(BaseModel):
    title: str
    synonyms: list[str]
    sources: list[str]
    animeSeason: Season


with open(
    os.path.join(
        os.path.dirname(__file__),
        'data',
        'mpaod',
        'anime-offline-database.json',
    ),
    'rt',
) as aodf:
    by_title = {a['title']: Anime(**a) for a in ujson.load(aodf)['data']}
