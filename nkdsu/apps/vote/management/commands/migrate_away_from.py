from django.core.management.base import BaseCommand

from ...models import Track


class Command(BaseCommand):
    args = '<track id to be deleted> <track id to keep>'
    help = (
        'copy all plays and votes from one track to another and then remove '
        'the first'
    )

    def handle(self, to_remove_id, target_id, *args, **options):
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
        target.save()

        to_remove.delete()
