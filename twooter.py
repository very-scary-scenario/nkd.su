from tweepy.streaming import StreamListener
from tweepy import OAuthHandler
from tweepy import Stream

from vote import tasks

import json

from os import listdir

from django.conf import settings

consumer_key = settings.CONSUMER_KEY
consumer_secret = settings.CONSUMER_SECRET
access_token = settings.ACCESS_TOKEN
access_token_secret = settings.ACCESS_TOKEN_SECRET

#user_id = 831369847 # @nkdsu (testing)
user_id = 634047438 # @nekodesuradio (production)

def parse(data):
    tweet = json.loads(data)

    if 'text' not in tweet:
        # this could be a deletion or some shit
        return True

    if tweet['text'].startswith('@nkdsu'):
        # this is potentially a request
        print tweet['text']
        tasks.log_vote.delay(tweet)

    elif tweet['user']['id'] == user_id:
        # this is potentially an np
        print tweet['text']
        tasks.log_play.delay(tweet)


class TweetListener(StreamListener):
    def on_data(self, data):
        parse(data)
        return True

    def on_error(self, status):
        print status
        return True

def peruse():
    archive_dir = '/Users/nivi/code/hrldcpr/twitter-archive/tweets/users/nekodesuradio/'
    tweetfiles = listdir(archive_dir)
    for tweetfile in tweetfiles:
        tf = open(archive_dir + tweetfile)
        parse(tf.read())
        tf.close()


def react():
    l = TweetListener()

    auth = OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)

    stream = Stream(auth, l, headers={'User-Agent': 'nkd.su'})
    # stream.filter(track=['@nkdsu'], follow=[]) # @nkdsu
    stream.filter(track=['@nkdsu'], follow=[str(user_id)]) # @nekodesuradio

#peruse()
react()
