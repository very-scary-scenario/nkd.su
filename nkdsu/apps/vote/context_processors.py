from django.urls import reverse

from .forms import DarkModeForm
from .models import Show, Track
from .utils import indefinitely


def get_sections(request):
    active_section = None
    most_recent_track = Track.objects.public().latest('revealed')

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
        'name': section[0],
        'url': section[1],
        'active': section[0] == active_section
    } for section in [
        ('home', reverse('vote:index')),
        ('archive', reverse('vote:archive')),
        ('new tracks', most_recent_track.show_revealed().get_revealed_url()),
        ('roulette', reverse('vote:roulette', kwargs={'mode': 'hipster'})),
        ('stats', reverse('vote:stats')),
        ('donate', 'https://www.patreon.com/NekoDesu'),
        ('etc', 'https://nekodesu.co.uk/'),
    ]]


def get_parent(request):
    if request.META.get('HTTP_X_PJAX', False):
        return 'pjax.html'
    else:
        return 'base.html'


def get_dark_mode(request):
    return request.session.get('dark_mode')


def nkdsu_context_processor(request):
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
