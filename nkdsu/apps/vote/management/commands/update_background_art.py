from django.core.management.base import BaseCommand

from ...models import Track


class Command(BaseCommand):
    help = (
        "Update background art for tracks. You can specify a track ID as an "
        "argument if you only want to do one track."
    )

    def handle(self, track_id=None, *args, **options):
        if track_id is None:
            tracks = Track.objects.all()
        else:
            tracks = [Track.objects.get(pk=track_id)]

        for track in tracks:
            track.update_background_art()
