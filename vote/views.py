# Create your views here.

from django.template import RequestContext, loader
from vote.models import Track, Vote, showtime, is_on_air
from django.http import HttpResponse, Http404
from django.shortcuts import render_to_response
from django.utils import timezone
from django import forms
import re
from markdown import markdown

def split_id3_title(id3_title):
    """ Split a Title (role) ID3 title up """
    try:
        role = re.findall('\(.*?\)', id3_title)[-1]
    except IndexError:
        role = None
        title = id3_title
    else:
        title = id3_title.replace(role, '').strip()
        role = role[1:-1] # strip brackets

    return title, role

def build_context_for_tracks(tracks, hide_ineligible=False):
    """ Build a template-digestible context for a list/set of tracks """
    context = []

    for track in tracks:
        title, role = split_id3_title(track.id3_title)

        if track.last_played == None:
            last_played = ''
        else:
            last_played = track.last_played

        votes = Vote.objects.filter(track=track, date__gt=showtime(prev_cutoff=True)).order_by('date')

        # vote replicator for testan'
        #n = 30
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

    playlist = Track.objects.filter(last_played__gte=showtime(prev_cutoff=True)).order_by('last_played')

    context = {
            'playlist': build_context_for_tracks(playlist),
            'show': showtime(),
            'form': form,
            'tracks': build_context_for_tracks(trackset, hide_ineligible=False),
            'show': showtime(),
            }

    return render_to_response('index.html', RequestContext(request, context))


def everything(request):
    """ Every track """
    all_tracks = Track.objects.all().order_by('last_played')
    context = {
            'title': 'everything',
            'tracks': build_context_for_tracks(all_tracks),
            'show': showtime(),
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
            }

    return render_to_response('tracks.html', RequestContext(request, context))

def info(request):
    words = markdown(open('README.md').read())
    context = {
            'words': words,
            }
    return render_to_response('markdown.html', RequestContext(request, context))
