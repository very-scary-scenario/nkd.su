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
        with (
            open(MPAOD_FILE, 'wb') as mpaod_file,
            gzip.GzipFile(filename='', mode='w', compresslevel=9, fileobj=mpaod_file, mtime=0) as gz,
        ):
            gz.write(mpaod_json.content)
