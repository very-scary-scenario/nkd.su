import datetime
import re

import tweepy

from django.conf import settings
from django.utils import timezone
from django.utils.http import urlquote


_post_tw_auth = tweepy.OAuthHandler(settings.CONSUMER_KEY,
                                    settings.CONSUMER_SECRET)
_post_tw_auth.set_access_token(settings.READING_ACCESS_TOKEN,
                               settings.READING_ACCESS_TOKEN_SECRET)
reading_tw_api = tweepy.API(_post_tw_auth)


def when(date):
    """
    Convert a date into an appropriately relative human-readable date.
    """

    our_day = date.date()
    today = timezone.now().date()
    show_locale = timezone.get_current_timezone()

    date = date.astimezone(show_locale)

    if our_day == today:
        return date.strftime('%I:%M %p').lower()
    elif today - our_day <= datetime.timedelta(days=6):
        return date.strftime('%A at %I:%M %p').lower()
    else:
        return date.strftime('%a %b %d at %I:%M %p').lower()


def length_str(msec):
    """
    Convert a number of milliseconds into a human-readable representation of
    the length of a song.
    """

    seconds = msec/1000
    remainder_seconds = seconds % 60
    minutes = (seconds - remainder_seconds) / 60

    if minutes >= 60:
        remainder_minutes = minutes % 60
        hours = (minutes - remainder_minutes) / 60
        return '%i:%02d:%02d' % (hours, remainder_minutes, remainder_seconds)
    else:
        return '%i:%02d' % (minutes, remainder_seconds)


def memoize(method):
    """
    A method wrapper. Stores the result of `method` in an attribute of the host
    object so you don't have to calculate it multiple times.

    Do not use on objects that will persist across requests.
    """

    # XXX


def tweet_url(tweet):
    return 'https://twitter.com/intent/tweet?text=%s' % urlquote(tweet)


def vote_url(tracks):
    return tweet_url(vote_tweet(tracks))


def vote_tweet(tracks):
    """
    Return what a person should tweet to vote for `tracks`.
    """

    return '@%s %s' % (settings.READING_USERNAME,
                       ' '.join([t.public_url() for t in tracks]))


def vote_tweet_intent_url(tracks):
    tweet = vote_tweet(tracks)
    return 'https://twitter.com/intent/tweet?text=%s' % urlquote(tweet)


def tweet_len(tweet):
    placeholder_url = ''
    while len(placeholder_url) < settings.TWITTER_SHORT_URL_LENGTH:
        placeholder_url = placeholder_url + 'x'

    shortened = re.sub('https?://[^\s]+', placeholder_url, tweet)
    return len(shortened)


def split_id3_title(id3_title):
    """
    Take a 'Title (role)'-style ID3 title and return (title, role)
    """
    role = None

    bracket_depth = 0
    for i in range(1, len(id3_title)+1):
        char = id3_title[-i]
        if char == ')':
            bracket_depth += 1
        elif char == '(':
            bracket_depth -= 1

        if bracket_depth == 0:
            if i != 1:
                role = id3_title[len(id3_title)-i:]
            break

    if role:
        title = id3_title.replace(role, '').strip()
        role = role[1:-1]  # strip brackets
    else:
        title = id3_title

    return title, role
