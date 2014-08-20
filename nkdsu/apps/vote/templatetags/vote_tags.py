import datetime

from markdown import markdown as md

from django.template import Library
from django.utils import timezone
from django.utils.safestring import mark_safe

from ..utils import length_str

register = Library()


@register.filter
def votes_for(track, show):
    """
    Return all votes applicable to to `track` for `show`.
    """

    return track.votes_for(show)


@register.filter
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
    elif today - our_day <= datetime.timedelta(days=364):
        return date.strftime('%a %b %d at %I:%M %p').lower()
    else:
        return date.strftime('%a %b %d %Y at %I:%M %p').lower()


@register.filter
def percent(flt):
    """
    Convert a float into a percentage string.
    """

    if flt is None:
        return '[in flux]'

    return '{0:.0f}%'.format(flt * 100)


@register.filter
def total_length(tracks):
    return length_str(sum([t.msec for t in tracks]))


@register.filter
def markdown(text):
    return mark_safe(md(text))
