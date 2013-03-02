#!/usr/bin/env python2.7

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nekodesu.settings")

from sys import argv
import json
import tweepy

from django.conf import settings

import vote.tasks


consumer_key = settings.CONSUMER_KEY
consumer_secret = settings.CONSUMER_SECRET
access_token = settings.READING_ACCESS_TOKEN
access_token_secret = settings.READING_ACCESS_TOKEN_SECRET

auth = tweepy.OAuthHandler(settings.CONSUMER_KEY, settings.CONSUMER_SECRET)
auth.set_access_token(settings.POSTING_ACCESS_TOKEN,
                      settings.POSTING_ACCESS_TOKEN_SECRET)


class TweetListener(tweepy.StreamListener):
    def on_data(self, data):
        loaded = json.loads(data)
        print loaded.get('text', 'idk')
        vote.tasks.parse.delay(loaded)
        return True

    def on_error(self, status):
        print status
        return True


def react():
    l = TweetListener()

    stream = tweepy.Stream(auth, l)
    track = ['@%s' % settings.READING_USERNAME]
    stream.filter(track=track)


def refresh():
    vote.tasks.refresh.delay()


if 'refresh' in argv:
    refresh()
else:
    react()
