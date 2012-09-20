import time

import Levenshtein

from django.conf import settings

from celery import task

from models import Vote, Track

def tweettime(tweet):
    return time.strftime('%Y-%m-%d %H:%M:%S+00:00', time.strptime(tweet['created_at'], '%a %b %d %H:%M:%S +0000 %Y'))


def vote_is_allowable(the_vote, track):
    try:
        Vote.objects.get(track=track, user_id=the_vote.user_id)
    except Vote.DoesNotExist:
        if the_vote.track.elligible():
            return True

    return False

def strip_hashtags(text):
    for word in text.split():
        if word.startswith('#'):
            text = text.replace(word, '')

    return text

@task
def log_play(tweet):
    text = strip_hashtags(tweet['text'])
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
        match.last_played = tweettime(tweet)
        match.save()

@task
def log_vote(tweet):
    # get song id
    for word in tweet['text'].split():
        try:
            track = Track.objects.get(id=int(word))
        except ValueError:
            # is not a number
            pass
        except Vote.DoesNotExist:
            # is not ours
            pass
        else:
            break
    else:
        return # no appropriate track was found

    date = tweettime(tweet)

    # make Vote
    the_vote = Vote(
            screen_name=tweet['user']['screen_name'],
            user_id=tweet['user']['id'],
            tweet_id=tweet['id'],
            track=track,
            date=date,
            user_image=tweet['user']['profile_image_url'],
            text=tweet['text'],
            )

    if vote_is_allowable(the_vote, track):
        the_vote.save()

    return
