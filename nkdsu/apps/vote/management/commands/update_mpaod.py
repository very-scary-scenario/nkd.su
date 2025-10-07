import gzip

from django.core.management.base import BaseCommand
import requests

from nkdsu.apps.vote.anime import MPAOD_FILE


class Command(BaseCommand):
    def handle(self, *args, **kwargs) -> None:
        mpaod_json = requests.get(
            'https://github.com/manami-project/anime-offline-database/'
            'releases/download/latest/anime-offline-database-minified.json'
        )
        with gzip.open(MPAOD_FILE, 'wb') as mpaod_file:
            mpaod_file.write(mpaod_json.content)
