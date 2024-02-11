from pydantic import BaseModel
import os

import ujson


class Anime(BaseModel):
    title: str
    synonyms: list[str]


with open(os.path.join(
    os.path.dirname(__file__), 'data', 'mpaod', 'anime-offline-database.json',
), 'rt') as aodf:
    by_title = {
        a['title']: Anime(
            title=a['title'],
            synonyms=a['synonyms'],
        ) for a in ujson.load(aodf)['data']
    }
