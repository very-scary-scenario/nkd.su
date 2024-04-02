import os

from django.core.management.base import BaseCommand
import requests

from nkdsu.apps.vote import emoji


SOURCE = 'https://unicode.org/Public/emoji/latest/{}'


class Command(BaseCommand):
    def retrieve(self, fn: str) -> None:
        resp = requests.get(SOURCE.format(fn))
        resp.raise_for_status()

        with open(os.path.join(emoji.DIR, fn), 'wb') as f:
            f.write(resp.content)

    def handle(self, *args, **kwargs) -> None:
        for fn in [emoji.SEQUENCCES_FN, emoji.ZWJ_SEQUENCES_FN]:
            self.retrieve(fn)
