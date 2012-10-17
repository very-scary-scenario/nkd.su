from datetime import datetime

import Levenshtein

from celery import task

from models import Play, Vote, Track

from django.utils import timezone
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.conf import settings

from sys import exc_info

def tweettime(tweet):
    try:
        tweettime = datetime.strptime(tweet['created_at'], '%a %b %d %H:%M:%S +0000 %Y')
    except ValueError:
        #Thu, 20 Sep 2012 14:51:24 +0000
        tweettime = datetime.strptime(tweet['created_at'], '%a, %d %b %Y %H:%M:%S +0000')

    return timezone.make_aware(tweettime, timezone.utc)


def strip_after_hashtags(text):
    return text.split(' #')[0]

@task
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

@task
def log_vote(tweet):
    # get song ids
    date = tweettime(tweet)

    # make Vote
    if 'user' in tweet: # this is from the streaming api
        the_vote = Vote(
                screen_name=tweet['user']['screen_name'],
                user_id=tweet['user']['id'],
                tweet_id=tweet['id'],
                date=date,
                user_image=tweet['user']['profile_image_url'],
                text=tweet['text'],
                name=tweet['user']['name'],
                )

    else: # this is from the archive
        the_vote = Vote(
                screen_name=tweet['from_user'],
                user_id=tweet['from_user_id'],
                tweet_id=tweet['id'],
                date=date,
                user_image=tweet['profile_image_url'],
                text=tweet['text'],
                name=tweet['from_user_name'],
                )

    try:
        the_vote.clean()
    except ValidationError:
        the_vote.delete()
        print exc_info()
    else:
        the_vote.save()

@task
def delete_vote(tweet_id):
    try:
        Vote.objects.get(tweet_id=tweet_id).delete()
    except ObjectDoesNotExist:
        print 'ignoring lost tweet'
