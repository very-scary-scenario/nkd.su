from __future__ import annotations

import logging
import re
import string
from dataclasses import dataclass
from functools import partial
from typing import (
    Any,
    Callable,
    Generic,
    Iterable,
    NoReturn,
    Optional,
    TYPE_CHECKING,
    TypeVar,
    cast,
)
from urllib.parse import quote, urlencode

from classtools import reify as ct_reify
from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse
import musicbrainzngs
import requests
import tweepy

if TYPE_CHECKING:
    from .models import Profile, Track


logger = logging.getLogger(__name__)


_read_tw_auth = tweepy.OAuthHandler(settings.CONSUMER_KEY, settings.CONSUMER_SECRET)
_read_tw_auth.set_access_token(
    settings.READING_ACCESS_TOKEN, settings.READING_ACCESS_TOKEN_SECRET
)
reading_tw_api = tweepy.API(_read_tw_auth)

_post_tw_auth = tweepy.OAuthHandler(settings.CONSUMER_KEY, settings.CONSUMER_SECRET)
_post_tw_auth.set_access_token(
    settings.POSTING_ACCESS_TOKEN, settings.POSTING_ACCESS_TOKEN_SECRET
)
posting_tw_api = tweepy.API(_post_tw_auth)


indefinitely: int = (
    (60 * 60 * 24 * 7) + (60 * 60) + 60
)  # one week, one hour and one minute


@dataclass
class BrowsableItem:
    url: Optional[str]
    name: str
    visible: bool = True

    def group(self) -> tuple[int, str]:
        """
        Return a sort order and a user-facing name for the group to put this
        item in. By default, an initial letter.
        """

        if not self.name:
            return (3, '')

        first_character = self.name[0]

        if first_character in string.ascii_letters:
            return (0, first_character.lower())
        elif first_character in string.digits:
            return (1, '0-9')
        else:
            return (2, '#')


@dataclass
class BrowsableYear(BrowsableItem):
    def group(self) -> tuple[int, str]:
        decade = (int(self.name) // 10) * 10
        return (decade, f"{decade}s")


def _get_short_url_length() -> int:
    cache_key = 'tw-short-url-length'
    length = cache.get(cache_key)
    if length is not None:
        return length
    try:
        length = reading_tw_api.configuration()['short_url_length_https']
    except tweepy.error.TweepError as e:
        logger.critical(
            "could not read twitter configuration to determine short URL length:\n{}".format(
                e
            )
        )
        length = 22

    cache.set(cache_key, length)
    return length


def _get_reading_username() -> str:
    cache_key = 'tw-reading-username:{}'.format(settings.READING_ACCESS_TOKEN)
    username = cache.get(cache_key)
    if username is not None:
        return username

    try:
        username = reading_tw_api.auth.get_username()
    except tweepy.error.TweepError as e:
        logger.critical("could not read reading account's username:\n{}".format(e))
        return 'nkdsu'
    else:
        cache.set(cache_key, username)
        return username


SHORT_URL_LENGTH: int = _get_short_url_length()
READING_USERNAME: str = _get_reading_username()


def length_str(msec: float) -> str:
    """
    Convert a number of milliseconds into a human-readable representation of
    the length of a track.
    """

    seconds = (msec or 0) / 1000
    remainder_seconds = seconds % 60
    minutes = (seconds - remainder_seconds) / 60

    if minutes >= 60:
        remainder_minutes = minutes % 60
        hours = (minutes - remainder_minutes) / 60
        return '%i:%02d:%02d' % (hours, remainder_minutes, remainder_seconds)
    else:
        return '%i:%02d' % (minutes, remainder_seconds)


def tweet_url(tweet: str) -> str:
    return 'https://twitter.com/intent/tweet?in_reply_to={reply_id}&text={text}'.format(
        reply_id='744237593164980224', text=quote(tweet)
    )


def vote_url(tracks: Iterable[Track]) -> str:
    return tweet_url(vote_tweet(tracks))


def vote_tweet(tracks: Iterable[Track]) -> str:
    """
    Return what a person should tweet to request `tracks`.
    """

    return ' '.join([t.get_public_url() for t in tracks])


def vote_tweet_intent_url(tracks: Iterable[Track]) -> str:
    # XXX rename this function, since it's no longer making a tweet URL
    base = reverse('vote:vote')
    query = {'t': ','.join(t.id for t in tracks)}
    return f'{base}?{urlencode(query)}'


def tweet_len(tweet: str) -> int:
    placeholder_url = ''
    while len(placeholder_url) < SHORT_URL_LENGTH:
        placeholder_url = placeholder_url + 'x'

    shortened = re.sub(r'https?://[^\s]+', placeholder_url, tweet)
    return len(shortened)


def split_id3_title(id3_title: str) -> tuple[str, Optional[str]]:
    """
    Take a 'Title (role)'-style ID3 title and return (title, role)
    """
    role = None

    bracket_depth = 0
    for i in range(1, len(id3_title) + 1):
        char = id3_title[-i]
        if char == ')':
            bracket_depth += 1
        elif char == '(':
            bracket_depth -= 1

        if bracket_depth == 0:
            if i != 1:
                role = id3_title[len(id3_title) - i :]
            break

    if role:
        title = id3_title.replace(role, '').strip()
        role = role[1:-1]  # strip brackets
    else:
        title = id3_title

    return title, role


# http://zeth.net/post/327/
def split_query_into_keywords(query: str) -> list[str]:
    """Split the query into keywords,
    where keywords are double quoted together,
    use as one keyword."""
    keywords = []
    # Deal with quoted keywords
    while '"' in query:
        first_quote = query.find('"')
        second_quote = query.find('"', first_quote + 1)
        if second_quote == -1:
            break
        quoted_keywords = query[first_quote : second_quote + 1]
        keywords.append(quoted_keywords.strip('"'))
        query = query.replace(quoted_keywords, ' ')
    # Split the rest by spaces
    keywords.extend(query.split())
    return keywords


T = TypeVar('T')


class Memoize(Generic[T]):
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

    def __init__(self, func: Callable[..., T]) -> None:
        self.func = func

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self.func
        return partial(self, obj)

    def __call__(self, *args: Any, **kw: Any) -> T:
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


def memoize(func: Callable[..., T]) -> Callable[..., T]:
    return Memoize(func)


def reify(func: Callable[[Any], T]) -> T:
    return cast(T, ct_reify(func))


def pk_cached(seconds: int) -> Callable[[T], T]:
    # does nothing (currently), but expresses a desire to cache stuff in future
    def wrapper(func: T) -> T:
        def wrapped(obj, *a, **k):
            def do_thing(func, pk, *a, **k):
                return func(obj, *a, **k)

            return do_thing(func, obj.pk, *a, **k)

        return cast(T, wrapped)

    return wrapper


def lastfm(**kwargs):
    params = {
        'api_key': settings.LASTFM_API_KEY,
        'api_secret': settings.LASTFM_API_SECRET,
        'format': 'json',
    }

    params.update(kwargs)

    resp = requests.get('http://ws.audioscrobbler.com/2.0/', params=params)
    return resp.json()


def assert_never(value: NoReturn) -> NoReturn:
    assert False, f'this code should not have been reached; got {value!r}'


def get_profile_for(user: User) -> Profile:
    try:
        return user.profile
    except ObjectDoesNotExist:
        from .models import Profile

        return Profile.objects.create(user=user)


musicbrainzngs.set_useragent('nkd.su', '0', 'http://nkd.su/')
