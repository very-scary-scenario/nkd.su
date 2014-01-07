from django.core.urlresolvers import reverse

from .models import Show
from .utils import indefinitely


def get_sections(request):
    active_section = None

    if (
        hasattr(request, 'resolver_match') and
        hasattr(request.resolver_match, 'func')
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
        ('new tracks', reverse('vote:added')),
        ('roulette', reverse('vote:roulette', kwargs={'mode': 'hipster'})),
        ('stats', reverse('vote:stats')),
        ('irc', 'irc://irc.rizon.net/NekoDesu'),
        ('webchat',
         'https://qchat.rizon.net/?channels=NekoDesu&uio=Mj10cnVlJjk9MAde'),
        ('neko desu', 'http://thisisthecat.com/index.php/neko-desu'),
    ]]


def get_parent(request):
    if request.META.get('HTTP_X_PJAX', False):
        return 'pjax.html'
    else:
        return 'base.html'


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
    }
