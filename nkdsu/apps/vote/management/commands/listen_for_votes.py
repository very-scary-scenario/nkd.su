import json

from django.conf import settings
from django.core.management.base import BaseCommand
import tweepy

from ...models import Vote
from ...utils import _read_tw_auth


class TweetListener(tweepy.StreamListener):
    def on_data(self, data):
        Vote.handle_tweet(json.loads(data))

    def on_error(self, status):
        print(status)
        return True


class Command(BaseCommand):
    def handle(self, *args, **options):
        listener = TweetListener()

        stream = tweepy.Stream(_read_tw_auth, listener)
        track = ['@%s' % settings.READING_USERNAME]
        stream.filter(track=track)
