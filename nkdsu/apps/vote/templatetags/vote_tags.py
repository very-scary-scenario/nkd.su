from django.template import Library

register = Library()


@register.filter
def votes_for(track, show):
    """
    Return all votes applicable to to `track` for `show`.
    """

    return track.votes_for(show)
