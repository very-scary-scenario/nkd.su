import tweepy
from tweepy.parsers import JSONParser

from django.core.management.base import BaseCommand

from ...utils import _read_tw_auth
from ...models import Vote


class Command(BaseCommand):
    def handle(self, *args, **options):
        t = tweepy.API(_read_tw_auth, parser=JSONParser())
        mentions = t.mentions_timeline(count=200, include_entities=True,
                                       tweet_mode='extended')

        for tweet in mentions:
            if not 'full_text' in tweet and len(tweet['text']) == 140:
                tweet = t.get_status(tweet['id'], tweet_mode='extended')

            Vote.handle_tweet(tweet)
