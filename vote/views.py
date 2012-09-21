# Create your views here.

from django.template import RequestContext, loader
from vote.models import Track, Vote, Play, showtime, is_on_air, split_id3_title
from django.http import HttpResponse, Http404
from django.shortcuts import render_to_response, redirect
from django.utils import timezone
from django import forms
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.utils.http import urlquote

from datetime import date, timedelta

from markdown import markdown


def build_context_for_tracks(
        tracks,
        hide_ineligible=False,
        sort_by_votes=False,
        get_last_played=True
        ):
    """ Build a template-digestible context for a list/set of tracks """
    context = []

    for track in tracks:
        title, role = split_id3_title(track.id3_title)

        if get_last_played:
            last_played = track.last_played()
            if last_played== None:
                last_played = ''
        else:
            last_played = None

        votes = Vote.objects.filter(track=track, date__gt=showtime(prev_cutoff=True)).order_by('date')

        # vote replicator for testan'
        #n = 15
        #new_votes = []
        #while n > 0:
        #    for vote in votes:
        #        new_votes.append(vote)
        #    n -= 1
        #votes = new_votes

        if (not hide_ineligible) or track.eligible():
            context.append({
                'title': title,
                'role': role,
                'artist': track.id3_artist,
                'id': track.id,
                'votes': votes,
                'last_played': last_played,
                'eligible': track.eligible(),
                })

    # sort by votes
    if sort_by_votes:
        context.sort(key=lambda track: len(track['votes']), reverse=True)

    return context

class SearchForm(forms.Form):
    """ Search form """
    q = forms.CharField()

def summary(request):
    """ Our landing page """
    trackset = set()

    if request.method == 'POST':
        form = SearchForm(request.POST)
        if form.is_valid():
            return search(request, form)
    else:
        form = SearchForm()

    for vote in Vote.objects.filter(date__gte=showtime(prev_cutoff=True)).order_by('date'):
        trackset.add(vote.track)

    # playlist = Track.objects.filter(last_played__gte=showtime(prev_cutoff=True)).order_by('last_played')
    playlist = [p.track for p in Play.objects.filter(datetime__gte=showtime(prev_cutoff=True)).order_by('datetime')]

    context = {
            'playlist': build_context_for_tracks(playlist),
            'form': form,
            'tracks': build_context_for_tracks(trackset, hide_ineligible=False, sort_by_votes=True),
            'show': showtime(),
            'on_air': is_on_air(),
            }

    return render_to_response('index.html', RequestContext(request, context))


def everything(request):
    """ Every track """
    tracks = Track.objects.all().order_by('last_played')
    context = {
            'title': 'everything',
            'tracks': build_context_for_tracks(tracks),
            'show': showtime(),
            'on_air': is_on_air(),
            }

    return render_to_response('tracks.html', RequestContext(request, context))

def roulette(request):
    """ Five random tracks """
    any_tracks = Track.objects.filter().order_by('?')
    tracks = []
    pos = 0
    while len(tracks) < 5 and pos < len(any_tracks):
        track = any_tracks[pos]
        if track.eligible():
            tracks.append(track)
        pos += 1

    context = {
            'title': 'roulette',
            'tracks': build_context_for_tracks(tracks),
            'show': showtime(),
            'on_air': is_on_air(),
            }

    return render_to_response('tracks.html', RequestContext(request, context))

# http://zeth.net/post/327/
def split_query_into_keywords(query):
    """Split the query into keywords,
    where keywords are double quoted together,
    use as one keyword."""
    keywords = []
    # Deal with quoted keywords
    while '"' in query:
        first_quote = query.find('"')
        second_quote = query.find('"', first_quote + 1)
        quoted_keywords = query[first_quote:second_quote + 1]
        keywords.append(quoted_keywords.strip('"'))
        query = query.replace(quoted_keywords, ' ')
    # Split the rest by spaces
    keywords.extend(query.split())
    return keywords

def search_for_tracks(keywords):
    """Make a search that contains all of the keywords."""
    tracks = Track.objects.all()
    trackset = set(tracks)
    for keyword in keywords:
        trackset = {t for t in trackset if keyword.lower() in t.canonical_string().lower()}
    return trackset


def search(request, form):
    """ Selected tracks """
    keywords = form.cleaned_data['q']
    keyword_list = split_query_into_keywords(keywords)
    trackset = search_for_tracks(keyword_list)

    context = {
            'title': keywords,
            'query': keywords,
            'tracks': build_context_for_tracks(trackset),
            'show': showtime(),
            'on_air': is_on_air(),
            }

    return render_to_response('tracks.html', RequestContext(request, context))


def artist(request, artist):
    """ All tracks by a particular artist """
    artist_tracks = Track.objects.filter(id3_artist=artist).order_by('id3_title')
    if not artist_tracks:
        raise Http404

    context = {
            'title': artist.lower(),
            'tracks': build_context_for_tracks(artist_tracks),
            'show': showtime(),
            'on_air': is_on_air(),
            }

    return render_to_response('tracks.html', RequestContext(request, context))

def latest_show(request):
    """ Redirect to the latest show """
    latest_play = Play.objects.all().order_by('-datetime')[0]
    return(redirect('/show/%s' % latest_play.datetime.strftime('%d-%m-%Y'))) 

def show(request, showdate):
    """ All tracks from a particular show """
    d, m, y = [int(n) for n in showdate.split('-')]
    start = date(y, m, d)
    end = start + timedelta(1)

    plays = list(Play.objects.filter(datetime__gt=start, datetime__lt=end).order_by('datetime'))

    try:
        next_play = Play.objects.filter(datetime__gt=plays[-1].datetime).order_by('datetime')[0]
    except IndexError:
        next_show = None
    else:
        next_show = next_play.datetime

    try:
        prev_play = Play.objects.filter(datetime__lt=plays[0].datetime).order_by('-datetime')[0]
    except IndexError:
        prev_show = None
    else:
        prev_show = prev_play.datetime


    if not plays:
        raise Http404

    context = {
            'title': showdate,
            'this_show': start,
            'tracks': build_context_for_tracks([p.track for p in plays], get_last_played=False),
            'on_air': is_on_air(),
            'next_show': next_show,
            'prev_show': prev_show,
            }

    return render_to_response('show.html', RequestContext(request, context))


def info(request):
    words = markdown(open(settings.SITE_ROOT + 'README.md').read())
    context = {
            'title': 'what?',
            'words': words,
            }
    return render_to_response('markdown.html', RequestContext(request, context))

@login_required
def mark_as_played(request, track_id):
    track = Track.objects.get(id=track_id)
    if track:
        play = Play(
                datetime = timezone.now(),
                track = track
                )
        play.save()
    else:
        raise Http404

    return(redirect('https://twitter.com/intent/tweet?text=%s' % urlquote(track.canonical_string() + ' #NekoDesu')))
