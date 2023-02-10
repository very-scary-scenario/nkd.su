from __future__ import annotations

import datetime
from typing import Iterable, Optional

from django.contrib.auth.models import AnonymousUser, User
from django.db.models import QuerySet
from django.template import Library
from django.utils import timezone
from django.utils.safestring import SafeText, mark_safe
from markdown import markdown as md

from ..models import Show, Track
from ..utils import length_str

register = Library()


@register.filter
def votes_for(track, show: Show) -> QuerySet[Track]:
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
def percent(flt: Optional[float]) -> str:
    """
    Convert a float into a percentage string.
    """

    if flt is None:
        return '[in flux]'

    return '{0:.0f}%'.format(flt * 100)


@register.filter
def total_length(tracks: Iterable[Track]):
    return length_str(sum([t.msec for t in tracks if t.msec is not None]))


@register.filter
def markdown(text: str) -> SafeText:
    return mark_safe(md(text))


@register.filter
def is_elf(user: User) -> bool:
    from ..elfs import ELFS

    return user.is_staff or user.groups.filter(pk=ELFS.pk).exists()


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
