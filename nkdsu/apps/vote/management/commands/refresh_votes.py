from django.core.management.base import BaseCommand

from ...utils import reading_tw_api
from ...models import Vote


class Command(BaseCommand):
    def handle(self, *args, **options):
        mentions = reading_tw_api.mentions_timeline(count=200,
                                                    include_entities=True)

        for tweet in mentions:
            Vote.handle_tweet(tweet)
