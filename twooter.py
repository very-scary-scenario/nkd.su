import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nekodesu.settings")

import twitter

from vote import tasks
from vote.models import Vote, Play

import json

from django.conf import settings

from sys import argv
from pprint import pprint
from urllib2 import HTTPError


consumer_key = settings.CONSUMER_KEY
consumer_secret = settings.CONSUMER_SECRET
access_token = settings.READING_ACCESS_TOKEN
access_token_secret = settings.READING_ACCESS_TOKEN_SECRET

def react():
    stream = twitter.TwitterStream(auth=twitter.OAuth(access_token, access_token_secret, consumer_key, consumer_secret))

    # override twitter.py's falsities
    stream.domain = 'userstream.twitter.com'
    stream.uriparts = ('2',)

    tweeterator = stream.user(replies='all')

    for tweet in tweeterator:
        tasks.parse.delay(dict(tweet))


def refresh():
    tasks.refresh.delay()


def parse_dir(directory):
    tweetfiles = os.listdir(directory)

    for tweetfile in tweetfiles:
        tf = open(directory + tweetfile)
        tasks.parse.delay(json.loads(tf.read()))
        tf.close()

def peruse():
    #np_dir = settings.TWITTER_ARCHIVE + '/users/nekodesuradio/'
    #parse_dir(np_dir)

    request_dir = settings.TWITTER_ARCHIVE + '/searches/%40nkdsu/'
    parse_dir(request_dir)

if 'peruse' in argv:
    peruse()
elif 'refresh' in argv:
    refresh()
else:
    react()
