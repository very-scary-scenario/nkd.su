from django.core.management.base import BaseCommand

from ...models import Track


class Command(BaseCommand):
    help = (
        'copy all plays and votes from one track to another and then remove '
        'the first'
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument('to_remove_id', type=str)
        parser.add_argument('target_id', type=str)

    def handle(self, to_remove_id, target_id, *args, **options) -> None:
        to_remove = Track.objects.get(id=to_remove_id)
        target = Track.objects.get(id=target_id)

        for vote in to_remove.vote_set.all():
            rm = vote.tracks
            rm.remove(to_remove)
            rm.add(target)
            vote.save()

        to_remove.play_set.all().update(track=target)
        to_remove.note_set.all().update(track=target)

        target.revealed = to_remove.revealed
        target.hidden = False
        target.media_id = to_remove.media_id
        target.save()

        to_remove.delete()
