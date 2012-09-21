import time

import Levenshtein

from django.conf import settings

from celery import task

from models import Play, Vote, Track, showtime

def tweettime(tweet):
    try:
        return time.strftime('%Y-%m-%d %H:%M:%S+00:00', time.strptime(tweet['created_at'], '%a %b %d %H:%M:%S +0000 %Y'))
    except ValueError:
        #Thu, 20 Sep 2012 14:51:24 +0000
        return time.strftime('%Y-%m-%d %H:%M:%S+00:00', time.strptime(tweet['created_at'], '%a, %d %b %Y %H:%M:%S +0000'))


def vote_is_allowable(the_vote, track):
    # as long as there are no votes in the current voting period from this person for this track...
    if not Vote.objects.filter(track=track, user_id=the_vote.user_id, date__gt=showtime(prev_cutoff=True)):
        # ...and as long as this track is eligible...
        if the_vote.track.eligible():
            return True

    return False

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

    if match and match.eligible():
        play = Play(
                datetime=tweettime(tweet),
                track=match
                )

        play.save()


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
    if 'user' in tweet: # this is from the streaming api
        the_vote = Vote(
                screen_name=tweet['user']['screen_name'],
                user_id=tweet['user']['id'],
                tweet_id=tweet['id'],
                track=track,
                date=date,
                user_image=tweet['user']['profile_image_url'],
                text=tweet['text'],
                )

    else: # this is from the archive
        the_vote = Vote(
                screen_name=tweet['from_user'],
                user_id=tweet['from_user_id'],
                tweet_id=tweet['id'],
                track=track,
                date=date,
                user_image=tweet['profile_image_url'],
                text=tweet['text'],
                )

    if vote_is_allowable(the_vote, track):
        the_vote.save()

