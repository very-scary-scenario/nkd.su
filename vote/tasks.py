from datetime import datetime
from sys import exc_info
import json

import Levenshtein
from celery import task
from commands import getoutput
import tweepy

from django.utils import timezone
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.conf import settings

from models import Play, Vote, Track


def tweettime(tweet):
    try:
        tweettime = datetime.strptime(tweet['created_at'],
                                      '%a %b %d %H:%M:%S +0000 %Y')
    except ValueError:
        #Thu, 20 Sep 2012 14:51:24 +0000
        tweettime = datetime.strptime(tweet['created_at'],
                                      '%a, %d %b %Y %H:%M:%S +0000')

    return timezone.make_aware(tweettime, timezone.utc)


def strip_after_hashtags(text):
    return text.split(' #')[0]


@task()
def log_play(tweet):
    text = strip_after_hashtags(tweet['text'])
    match = None
    matches = []
    tracks = Track.objects.all()

    for track in tracks:
        if track.canonical_string() in text:
            matches.append(track)

    if matches:
        match = min(matches, key=lambda t: len(t.canonical_string()))
    else:
        for track in tracks:
            leven = Levenshtein.ratio(text, track.canonical_string())
            if leven > .7:
                matches.append((leven, track))

        if matches:
            match = max(matches)[1]

    if match:
        play = Play(
            datetime=tweettime(tweet),
            track=match
        )

        try:
            play.clean()
        except ValidationError:
            print exc_info()
        else:
            play.save()


@task()
def log_vote(tweet, should_not_be_new=False):
    # get song ids
    date = tweettime(tweet)

    if should_not_be_new and not Vote.objects.filter(
            tweet_id=tweet['id']).exists():
        print 'this vote did not exist, killing stream...'
        # we should kill the streaming process to force it to reconnect
        pid = getoutput(
            "ps aux | awk '/ python... twooter/ && !/awk/ { print $2 }'")
        getoutput('kill %s' % pid)

    elif Vote.objects.filter(tweet_id=tweet['id']).exists():
        # this vote exists already, we can ignore it
        return

    # make Vote
    the_vote = Vote(
        screen_name=tweet['user']['screen_name'],
        user_id=tweet['user']['id'],
        tweet_id=tweet['id'],
        date=date,
        user_image=tweet['user']['profile_image_url'],
        text=tweet['text'],
        name=tweet['user']['name'],
    )

    try:
        urls = [url['expanded_url'] for url in tweet['entities']['urls']]
    except KeyError:
        tracks = False
        # no tracks; abandon ship!
    else:
        tracks = [t for t in the_vote.derive_tracks_from_url_list(urls)
                  if t not in the_vote.relevant_prior_voted_tracks()]

    if tracks:
        try:
            the_vote.clean()
        except ValidationError:
            print exc_info()
        else:
            the_vote.save()
            the_vote.tracks = tracks
            the_vote.save()
    else:
        print 'not saving'


@task()
def delete_vote(tweet_id):
    try:
        Vote.objects.get(tweet_id=tweet_id).delete()
    except ObjectDoesNotExist:
        print 'ignoring lost tweet'


class JsonParser(tweepy.parsers.Parser):
    def parse(self, method, payload):
        return json.loads(payload)


@task()
def refresh():
    consumer_key = settings.CONSUMER_KEY
    consumer_secret = settings.CONSUMER_SECRET
    access_token = settings.READING_ACCESS_TOKEN
    access_token_secret = settings.READING_ACCESS_TOKEN_SECRET

    read_tw_auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    read_tw_auth.set_access_token(access_token, access_token_secret)
    t = tweepy.API(read_tw_auth, parser=JsonParser())

    tweets = t.mentions_timeline(count='50', include_entities=True)

    for tweet in tweets:
        parse(tweet, should_not_be_new=True)


@task()
def parse(tweet, should_not_be_new=False):
    """ Deal with a tweet, post-json conversion.

    If should_not_be_new is True and we come across a new vote, the streaming
    process is probably borked and we should do something about it. """

    if 'text' not in tweet:
        # this could be a deletion or some shit
        if 'delete' in tweet:
            print 'deleting tweet %s' % tweet['delete']['status']['id']
            delete_vote(tweet['delete']['status']['id'])

        return

    if tweet['text'].startswith('@%s ' % settings.READING_USERNAME):
        # this is potentially a request
        try:
            print '%s: %s' % (tweet['user']['screen_name'], tweet['text'])
        except KeyError:
            print '%s: %s' % (tweet['from_user'], tweet['text'])

        log_vote(tweet, should_not_be_new=should_not_be_new)
