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

def parse(tweet):
    if 'text' not in tweet:
        # this could be a deletion or some shit
        print tweet
        if 'delete' in tweet:
            print 'deleting tweet %s' % tweet['delete']['status']['id']
            tasks.delete_vote.delay(tweet['delete']['status']['id'])

        return

    if tweet['text'].startswith('@%s ' % settings.READING_USERNAME):
        # this is potentially a request
        try:
            print '%s: %s' % (tweet['user']['screen_name'], tweet['text'])
        except KeyError:
            print '%s: %s' % (tweet['from_user'], tweet['text'])

        tasks.log_vote.delay(tweet)

def react():
    stream = twitter.TwitterStream(auth=twitter.OAuth(access_token, access_token_secret, consumer_key, consumer_secret))

    # override twitter.py's falsities
    stream.domain = 'userstream.twitter.com'
    stream.uriparts = ('2',)

    tweeterator = stream.user(replies='all')

    for tweet in tweeterator:
        parse(dict(tweet))


def parse_dir(directory):
    tweetfiles = os.listdir(directory)

    for tweetfile in tweetfiles:
        tf = open(directory + tweetfile)
        parse(json.loads(tf.read()))
        tf.close()

def refresh():
    t = twitter.Twitter(auth=twitter.OAuth(access_token, access_token_secret, consumer_key, consumer_secret))
    tweets = t.statuses.mentions()

    for tweet in tweets:
        parse(tweet)
    
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
