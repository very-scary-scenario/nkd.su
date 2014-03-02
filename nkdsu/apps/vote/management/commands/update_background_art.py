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

        has_art = 0
        missing_art = 0

        for track in tracks:
            track.update_background_art()

            if track.background_art:
                has_art += 1
            else:
                missing_art += 1

        print 'art found for %i of %i tracks' % (has_art,
                                                 has_art + missing_art)
