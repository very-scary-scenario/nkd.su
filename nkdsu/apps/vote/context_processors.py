from django.core.urlresolvers import reverse

from .models import Show


def nkdsu_context_processor(request):
    """
    Add common stuff to context.
    """

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

    sections = [{
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

    current_show = Show.current()

    return {
        'current_show': current_show,
        'vote_show': current_show,
        'sections': sections,
    }
