from django.core.urlresolvers import reverse

from .models import Show


def nkdsu_context_processor(request):
    """
    Add common stuff to context.
    """

    sections = [{
        'name': section[0],
        'url': section[1],
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

    return {
        'current_show': Show.current(),
        'path': request.path,
        'sections': sections,
    }
