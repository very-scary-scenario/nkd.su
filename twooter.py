import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nekodesu.settings")

from tweepy.streaming import StreamListener
from tweepy import OAuthHandler
from tweepy import Stream

from vote import tasks
from vote.models import Vote, Play

import json

from django.conf import settings

from sys import argv


consumer_key = settings.CONSUMER_KEY
consumer_secret = settings.CONSUMER_SECRET
access_token = settings.ACCESS_TOKEN
access_token_secret = settings.ACCESS_TOKEN_SECRET

#user_id = 831369847 # @nkdsu (testing)
user_id = 634047438 # @nekodesuradio (production)

def parse(data):
    try:
        tweet = json.loads(data)
    except ValueError:
        return


    if 'text' not in tweet:
        # this could be a deletion or some shit
        if 'delete' in tweet:
            print 'deleting tweet %s' % tweet['delete']['id']
            tasks.delete_vote.delay(tweet['delete']['id'])

        return


    if tweet['text'].startswith('@nkdsu'):
        # this is potentially a request
        print tweet['text']
        tasks.log_vote.delay(tweet)

    #elif tweet['user']['id'] == user_id:
        # this is potentially an np
        # we no longer care; twootin's automatic
        #print tweet['text']
        #tasks.log_play.delay(tweet)


class TweetListener(StreamListener):
    def on_data(self, data):
        parse(data)
        return True

    def on_error(self, status):
        print status
        return True

def parse_dir(directory):
    tweetfiles = os.listdir(directory)

    for tweetfile in tweetfiles:
        tf = open(directory + tweetfile)
        parse(tf.read())
        tf.close()

def peruse():
    np_dir = settings.TWITTER_ARCHIVE + '/users/nekodesuradio/'
    parse_dir(np_dir)

    request_dir = settings.TWITTER_ARCHIVE + '/searches/%40nkdsu/'
    parse_dir(request_dir)

def react():
    l = TweetListener()

    auth = OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)

    stream = Stream(auth, l, headers={'User-Agent': 'nkd.su'})
    stream.filter(track=['@nkdsu']) #, follow=[str(user_id)])

if 'peruse' in argv:
    #print 'stripping...'
    #for play in Play.objects.all():
        #play.delete()

    #for vote in Vote.objects.all():
        #vote.delete()

    peruse()
else:
    react()
