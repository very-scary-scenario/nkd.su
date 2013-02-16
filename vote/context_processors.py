from vote.models import Week


def nkdsu_context_processor(request):
    """
    Add this_week and path to every context.
    """

    this_week = Week()
    
    section_list = [
        ('home', '/'),
        ('archive', '/show/'),
        ('new tracks', '/added/'),
        ('surprise me', '/roulette/'),
        ('stats', '/stats/'),
        ('irc', 'irc://irc.rizon.net/NekoDesu'),
        ('webchat', 'https://qchat.rizon.net/?channels=NekoDesu&uio=Mj10cnVlJjk9MAde'),
        ('twitter', 'http://twitter.com/search/realtime?q=%23NekoDesu'),
        ('neko desu', 'http://thisisthecat.com/index.php/neko-desu'),
    ]

    sections = []

    for section in section_list:
        section_dict = {
            'name': section[0],
            'url': section[1],
            'classes': '',
        }
        
        sections.append(section_dict)

    return {
        'this_week': this_week,
        'on_air': this_week.is_on_air(),
        'path': request.path,
        'session': request.session,
        'show': this_week.showtime,
        'new_tracks': len(this_week.added()),
        'sections': sections,
    }
