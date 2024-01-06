import re

from django.core.management.base import BaseCommand

from ...models import Track


class Command(BaseCommand):
    def handle(self, **options) -> None:
        seen_chars: set[str] = set()
        for track in Track.objects.all():
            if non_ascii_chars := re.sub(r'[ -~]', '', track.id3_title+track.id3_artist):
                new_chars = {c for c in non_ascii_chars if c not in seen_chars}
                if new_chars:
                    print(''.join(new_chars))
                    print(f'  {track}')

                seen_chars.update(new_chars)
