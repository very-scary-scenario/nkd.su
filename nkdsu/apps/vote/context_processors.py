from typing import Any, Dict

from django.http import HttpRequest
from django.urls import reverse

from .forms import DarkModeForm
from .models import Show, Track
from .utils import indefinitely


def get_sections(request):
    active_section = None
    try:
        most_recent_track = Track.objects.public().latest('revealed')
    except Track.DoesNotExist:
        most_recent_track = None

    if (
        hasattr(request, 'resolver_match') and
        hasattr(request.resolver_match, 'func') and
        request.resolver_match.func.__closure__
    ):
        for cell in request.resolver_match.func.__closure__:
            thing = cell.cell_contents
            if hasattr(thing, 'section'):
                active_section = thing.section
                break

    return [{
        'name': name,
        'url': url,
        'active': name == active_section
    } for name, url in [
        ('home', reverse('vote:index')),
        ('browse', reverse('vote:browse')),
        ('new tracks',
         most_recent_track.show_revealed().get_revealed_url()
         if most_recent_track else None),
        ('roulette', reverse('vote:roulette')),
        ('stats', reverse('vote:stats')),
        ('donate', 'https://www.patreon.com/NekoDesu'),
        ('etc', 'https://nekodesu.radio/'),
    ] if url]


def get_parent(request: HttpRequest) -> str:
    return 'base.html'


def get_dark_mode(request: HttpRequest):
    return request.session.get('dark_mode')


def nkdsu_context_processor(request: HttpRequest) -> Dict[str, Any]:
    """
    Add common stuff to context.
    """

    current_show = Show.current()

    return {
        'current_show': current_show,
        'vote_show': current_show,
        'sections': get_sections(request),
        'indefinitely': indefinitely,
        'parent': get_parent(request),
        'dark_mode': get_dark_mode(request),
        'dark_mode_form': DarkModeForm(),
    }
