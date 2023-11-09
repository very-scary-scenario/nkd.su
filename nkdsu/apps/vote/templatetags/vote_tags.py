from __future__ import annotations

import datetime
from typing import Iterable, Optional
from urllib.parse import unquote, urlparse

from allauth.account.models import EmailAddress
from django.contrib.auth.models import AnonymousUser, User
from django.db.models import QuerySet
from django.template import Library
from django.utils import timezone
from django.utils.safestring import SafeText, mark_safe
from markdown import markdown as md

from ..models import Play, Show, Track, Vote
from ..utils import length_str

register = Library()


@register.filter
def votes_for(track: Track, show: Show) -> QuerySet[Vote]:
    """
    Return all votes applicable to to `track` for `show`.
    """

    return track.votes_for(show)


@register.filter
def when(date: datetime.datetime) -> str:
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
    elif today - our_day <= datetime.timedelta(days=364):
        return date.strftime('%a %b %d at %I:%M %p').lower()
    else:
        return date.strftime('%a %b %d %Y at %I:%M %p').lower()


@register.filter
def weeks_ago(play: Play) -> int:
    show = Show.current()
    return ((show.end - play.date).days + 1) // 7


@register.filter
def percent(flt: Optional[float]) -> str:
    """
    Convert a float into a percentage string.

    >>> percent(2.5)
    '250%'
    >>> percent(2/3)
    '67%'
    >>> percent(None)
    '[in flux]'
    """

    if flt is None:
        return '[in flux]'

    return '{0:.0f}%'.format(flt * 100)


@register.filter
def format_otp(number: int) -> str:
    """
    Put non-breaking spaces into the string representation of a number every three digits (from the right).

    >>> format_otp(123)
    '123'
    >>> format_otp(123456)
    '123\u202f456'
    >>> format_otp(1234567)
    '1\u202f234\u202f567'
    """

    string = f'{number:d}'
    segments: list[str] = []

    while string:
        segments.append(string[-3:])
        string = string[:-3]

    return '\N{NARROW NO-BREAK SPACE}'.join(segments[::-1])


@register.filter
def total_length(tracks: Iterable[Track]):
    return length_str(sum([t.msec for t in tracks if t.msec is not None]))


@register.filter
def markdown(text: str) -> SafeText:
    """
    Render markdown content as HTML.

    :warning:
        Do not use with user-provided strings, or XSS attacks will immediately
        be possible.
    """

    return mark_safe(md(text))


@register.filter
def is_elf(user: User) -> bool:
    from ..elfs import is_elf

    return is_elf(user)


@register.filter
def has_verified_email(user: User) -> bool:
    return EmailAddress.objects.filter(user=user, verified=True).exists()


@register.filter
def eligible_for(track: Track, user: User | AnonymousUser) -> bool:
    return (
        (user.is_authenticated)
        and (
            track.pk
            not in (t.pk for t in user.profile.tracks_voted_for_for(Show.current()))
        )
        and track.eligible()
    )


@register.filter
def url_display(url: str) -> str:
    """
    Strip the scheme and unquote %-sequences in a URL, if present.

    >>> url_display('https://nkd.su/path?q=s#fragment')
    'nkd.su/path?q=s#fragment'
    >>> url_display('ftps://nkd.su/p%C3%A4th?q=s#fragment')
    'nkd.su/päth?q=s#fragment'
    >>> url_display('not a url')
    'not a url'
    """

    return unquote(url.removeprefix(f'{urlparse(url).scheme}://'))
