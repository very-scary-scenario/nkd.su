from typing import Iterable, Optional

from django.core.management.base import BaseCommand, CommandParser

from ...models import Track


class Command(BaseCommand):
    help = (
        "Update background art for tracks. You can specify a track ID as an "
        "argument if you only want to do one track."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            '--quick',
            action='store_true',
            default=False,
            help="Don't get art for tracks that already have art",
        )

    def handle(self, track_id: Optional[str] = None, *args, **options) -> None:
        tracks: Iterable[Track]

        if track_id is None:
            tracks = Track.objects.all()
            total = tracks.count()
        else:
            tracks = [Track.objects.get(pk=track_id)]
            total = len(tracks)

        has_art = 0
        missing_art = 0
        covered = 0

        for track in tracks:
            covered += 1

            if track.background_art and options.get('quick'):
                has_art += 1
                continue

            if int(options['verbosity']) > 1:
                print(f'{covered}/{total} - {track}')

            track.update_background_art()

            if track.background_art:
                has_art += 1
            else:
                missing_art += 1
