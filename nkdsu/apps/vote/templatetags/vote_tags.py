import datetime

from django.template import Library
from django.utils import timezone

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
    else:
        return date.strftime('%a %b %d at %I:%M %p').lower()
