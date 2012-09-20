import time

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


@task
def log_play(tweet):
    matches = []
    for track in Track.objects.all():
        if track.canonical_string() in tweet['text']:
            matches.append(track)

    if matches:
        track = min(matches, key=lambda s: len(s.canonical_string()))
        track.last_played = tweettime(tweet)
        track.save()

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
