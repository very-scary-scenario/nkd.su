from collections import Counter

from django.core.management.base import BaseCommand

from ...models import Track


class Command(BaseCommand):
    def counter(self, items, func):
        c = Counter()
        for item in items:
            c[item] = func(item)
        return c

    def handle(self, **options):
        print '\nby vote count, total:'
        for track, count in self.counter(
            Track.objects.all(),
            lambda t: t.vote_set.all().count(),
        ).most_common(50):
            print '{:>5}: {}'.format(count, track)

        print '\nby play count, total:'
        for track, count in self.counter(
            Track.objects.all(),
            lambda t: t.play_set.all().count(),
        ).most_common(50):
            print '{:>5}: {}'.format(count, track)
