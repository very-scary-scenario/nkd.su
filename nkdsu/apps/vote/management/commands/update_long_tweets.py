from django.core.management.base import BaseCommand
import tweepy
from tweepy.parsers import JSONParser

from ...models import Vote
from ...utils import _read_tw_auth


class Command(BaseCommand):
    def handle(self, *args, **options):

        t = tweepy.API(_read_tw_auth, parser=JSONParser())

        for vote in Vote.objects.exclude(tweet_id__isnull=True).order_by('-date'):
            if len(vote.text) != 280:
                continue

            print(vote.text)
            try:
                tweet_obj = t.get_status(vote.tweet_id, tweet_mode='extended')
            except tweepy.TweepError as e:
                print(e)
                continue
            vote.text = tweet_obj.get('full_text', None) or tweet_obj.get('text', None)
            print(vote.text)
            vote.save()
