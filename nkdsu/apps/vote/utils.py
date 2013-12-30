import re
from functools import partial

import tweepy

from django.conf import settings
from django.utils.http import urlquote


_post_tw_auth = tweepy.OAuthHandler(settings.CONSUMER_KEY,
                                    settings.CONSUMER_SECRET)
_post_tw_auth.set_access_token(settings.READING_ACCESS_TOKEN,
                               settings.READING_ACCESS_TOKEN_SECRET)
reading_tw_api = tweepy.API(_post_tw_auth)


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


# http://zeth.net/post/327/
def split_query_into_keywords(query):
    """Split the query into keywords,
    where keywords are double quoted together,
    use as one keyword."""
    keywords = []
    # Deal with quoted keywords
    while '"' in query:
        first_quote = query.find('"')
        second_quote = query.find('"', first_quote + 1)
        quoted_keywords = query[first_quote:second_quote + 1]
        keywords.append(quoted_keywords.strip('"'))
        query = query.replace(quoted_keywords, ' ')
    # Split the rest by spaces
    keywords.extend(query.split())
    return keywords


class Memoize(object):
    """
    Cache the return value of a method on the object itself.

    This class is meant to be used as a decorator of methods. The return value
    from a given method invocation will be cached on the instance whose method
    was invoked. All arguments passed to a method decorated with memoize must
    be hashable.

    If a memoized method is invoked directly on its class the result will not
    be cached. Instead the method will be invoked like a static method:
    class Obj(object):
        @memoize
        def add_to(self, arg):
            return self + arg
    Obj.add_to(1) # not enough arguments
    Obj.add_to(1, 2) # returns 3, result is not cached
    """

    def __init__(self, func):
        self.func = func

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self.func
        return partial(self, obj)

    def __call__(self, *args, **kw):
        obj = args[0]
        try:
            cache = obj.__cache
        except AttributeError:
            cache = obj.__cache = {}
        key = (self.func, args[1:], frozenset(kw.items()))
        try:
            res = cache[key]
        except KeyError:
            res = cache[key] = self.func(*args, **kw)
        return res


memoize = Memoize
