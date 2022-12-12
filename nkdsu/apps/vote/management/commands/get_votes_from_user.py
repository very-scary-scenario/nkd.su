from django.core.management.base import BaseCommand
import tweepy
from tweepy.parsers import JSONParser

from ...models import Vote
from ...utils import _read_tw_auth


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('screen_name', type=str)

    def handle(self, screen_name, *args, **options):
        t = tweepy.API(_read_tw_auth, parser=JSONParser())
        tweets = t.user_timeline(
            count=200,
            include_entities=True,
            tweet_mode='extended',
            screen_name=screen_name,
        )

        for tweet in tweets:
            if ('full_text' not in tweet) and (len(tweet['text']) == 140):
                tweet = t.get_status(tweet['id'], tweet_mode='extended')

            Vote.handle_tweet(tweet)
