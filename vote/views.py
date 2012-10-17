# Create your views here.
# -*- coding: utf-8 -*-

from django.core.exceptions import ValidationError
from django.template import RequestContext, loader
from vote.models import Track, Vote, ManualVote, Play, Block, Shortlist, Discard, Week, split_id3_title, is_on_air, vote_url
from vote.update_library import update_library
from django.http import HttpResponse, Http404
from django.shortcuts import render_to_response, redirect
from django.utils import timezone
from django import forms
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.utils.http import urlquote
from django.core.paginator import Paginator
from sys import exc_info
from cStringIO import StringIO
from email.mime.text import MIMEText

from vote.mail import sendmail
from datetime import date, timedelta, datetime

from markdown import markdown
import tweepy
import akismet

post_tw_auth = tweepy.OAuthHandler(settings.CONSUMER_KEY, settings.CONSUMER_SECRET)
post_tw_auth.set_access_token(settings.POSTING_ACCESS_TOKEN, settings.POSTING_ACCESS_TOKEN_SECRET)
tw_api = tweepy.API(post_tw_auth)

ak_api = akismet.Akismet(key=settings.AKISMET_API_KEY, blog_url=settings.AKISMET_BLOG_URL, agent='nkdsu/0.0')

class SearchForm(forms.Form):
    q = forms.CharField()

def summary(request, week=None):
    """ Our landing page """
    if not week:
        week = Week()
    trackset = set()

    form = SearchForm()

    # only consider votes from before the end of the current show, so we can work in the past
    [trackset.add(t) for v in week.votes() for t in v.tracks.all()]

    unfiltered_tracklist = sorted(trackset, reverse=True, key=lambda t: len(t.votes()))
    if request.user.is_authenticated():
        tracklist = [t for t in unfiltered_tracklist if t.eligible() and not week.shortlist_or_discard(t)]
        shortlist = week.shortlist()
        discard = week.discard()
    else:
        shortlist = None
        discard = None
        tracklist = [t for t in unfiltered_tracklist if t.eligible()]
    tracklist.extend([t for t in unfiltered_tracklist if t.ineligible() and (t.ineligible() != 'played this week')])

    # ditto plays
    playlist = week.plays(invert=True)

    context = {
            'session': request.session,
            'path': request.path,
            'playlist': [p.track for p in playlist],
            'form': form,
            'tracks': tracklist,
            'shortlist': shortlist,
            'discard': discard,
            'show': week.showtime,
            'on_air': is_on_air(),
            }

    return render_to_response('index.html', RequestContext(request, context))


def everything(request):
    """ Every track """
    context = {
            'session': request.session,
            'path': request.path,
            'title': 'everything',
            'tracks': Track.objects.all(),
            'path': request.path,
            'show': Week().showtime,
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
            'session': request.session,
            'path': request.path,
            'title': 'roulette',
            'tracks': tracks,
            'show': Week().showtime,
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
    return list(trackset)

def search_redirect(request):
    form = SearchForm(request.GET)

    if not form.is_valid():
        return redirect('/')
    else:
        query = form.cleaned_data['q']
        return redirect('/search/%s' % query)

def search(request, query, pageno=1):
    try:
        trackset = (Track.objects.get(id=query),)
    except Track.DoesNotExist:
        keyword_list = split_query_into_keywords(query)
        trackset = search_for_tracks(keyword_list)

    paginator = Paginator(trackset, 20)
    page = paginator.page(pageno)

    context = {
            'session': request.session,
            'path': request.path,
            'title': query,
            'query': query,
            'tracks': page.object_list,
            'show': Week().showtime,
            'on_air': is_on_air(),
            'page': page,
            }

    return render_to_response('tracks.html', RequestContext(request, context))


def artist(request, artist):
    """ All tracks by a particular artist """
    artist_tracks = Track.objects.filter(id3_artist=artist).order_by('id3_title')
    if not artist_tracks:
        raise Http404

    context = {
            'session': request.session,
            'path': request.path,
            'title': artist.lower(),
            'tracks': artist_tracks,
            'show': Week().showtime,
            'on_air': is_on_air(),
            }

    return render_to_response('tracks.html', RequestContext(request, context))

def latest_show(request):
    """ Redirect to the last week's show """
    last_week = Week().prev()
    return redirect('/show/%s' % last_week.showtime.strftime('%d-%m-%Y'))

def show(request, date):
    """ Playlist archive """
    day, month, year = (int(t) for t in date.split('-'))
    week = Week(timezone.make_aware(datetime(year, month, day), timezone.utc))
    plays = week.plays()

    # the world is lady

    if not plays:
        raise Http404

    next_week = week.next()
    if next_week.plays():
        next_show = next_week.showtime
    else:
        next_show = None

    prev_week = week.prev()
    if prev_week.plays():
        prev_show = prev_week.showtime
    else:
        prev_show = None

    tracks = [p.track for p in plays]

    denied = set()
    [denied.add(t) for v in week.votes() for t in v.tracks.all() if t not in tracks]

    [t.set_week(week) for t in tracks]
    [t.set_week(week) for t in denied]

    denied = sorted(denied, reverse=True, key=lambda t: len(t.votes()))

    context = {
            'session': request.session,
            'path': request.path,
            'title': date,
            'this_show': week.showtime,
            'tracks': tracks,
            'denied': denied,
            'on_air': is_on_air(),
            'next_show': next_show,
            'prev_show': prev_show,
            'show': Week().showtime,
            }

    return render_to_response('show.html', RequestContext(request, context))


def info(request):
    words = markdown(open(settings.SITE_ROOT + 'README.md').read())
    context = {
            'session': request.session,
            'path': request.path,
            'title': 'what?',
            'words': words,
            }
    return render_to_response('markdown.html', RequestContext(request, context))

class ManualVoteForm(forms.ModelForm):
    """ Make a manual vote! """
    class Meta:
        model = ManualVote

def confirm(request, action, deets=None):
    context = {
            'session': request.session,
            'path': request.path,
            'action': action,
            'deets': deets,
            }

    return render_to_response('confirm.html', RequestContext(request, context))

@login_required
def make_vote(request, track_id):
    track = Track.objects.get(id=track_id)

    if request.method == 'POST':
        vote = ManualVote(track=track)
        form = ManualVoteForm(request.POST, instance=vote)
        if form.is_valid():
            form.save()
            return redirect('/')
    else:
        form = ManualVoteForm()

    context = {
            'session': request.session,
            'path': request.path,
            'track': track,
            'form': form,
            'title': 'new vote',
            }

    return render_to_response('vote.html', RequestContext(request, context))

@login_required
def mark_as_played(request, track_id):
    try:
        track = Track.objects.get(id=track_id)
    except Track.DoesNotExist:
        raise Http404

    play = Play(
            datetime = timezone.now(),
            track = track
            )
    try:
        play.clean()
    except ValidationError:
        context = {'message': exc_info()[1].messages[0]}
        return render_to_response('message.html', RequestContext(request, context))

    else:
        if not ('confirm' in request.GET and request.GET['confirm'] == 'true'):
            return confirm(request, 'mark %s as played' % track.derived_title())
        else:
            # tweet it
            canon = track.canonical_string()
            if len(canon) > 140 - (len(settings.HASHTAG) + 1):
                canon = canon[0:140-(len(settings.HASHTAG)+2)]+u'…'
            status = u'%s %s' % (canon, settings.HASHTAG)
            tweet = tw_api.update_status(status)

            play.tweet_id = tweet.id

            # and finally save the tweet
            play.save()

    return redirect_nicely(request)

@login_required
def unmark_as_played(request, track_id):
    """ Deletes the latest Play for a track """
    try:
        track = Track.objects.get(id=track_id)
        latest_play = Play.objects.filter(track=track).order_by('-datetime')[0]
    except Track.DoesNotExist:
        raise Http404

    try:
        latest_play = Play.objects.filter(track=track).order_by('-datetime')[0]
    except IndexError:
        raise Http404

    if not ('confirm' in request.GET and request.GET['confirm'] == 'true'):
        return confirm(request, 'unmark %s as played' % track.derived_title())
    else:
        try:
            tw_api.destroy_status(id=latest_play.tweet_id)
        except tweepy.TweepError:
            pass
        latest_play.delete()
        return redirect_nicely(request)


class LibraryUploadForm(forms.Form):
    library_xml = forms.FileField(label='Library XML')

@login_required
def upload_library(request):
    """ Handling library uploads """
    form = LibraryUploadForm()

    if request.method == 'POST':
        form = LibraryUploadForm(request.POST, request.FILES)
        if form.is_valid():
            f = open(settings.TMP_XML_PATH, 'w')
            f.write(request.FILES['library_xml'].read())
            f.close()

            f = open(settings.TMP_XML_PATH, 'r')
            changes = update_library(f, dry_run=True)

            if changes:
                summary = '\n'.join(changes)
            else:
                summary = 'no changes'
            response = confirm(request, 'update the library', summary)
            f.close()

            return response

    elif (not ('confirm' in request.GET and request.GET['confirm'] == 'true')) or (request.method == 'POST' and not form.is_valid()):
        # this is an initial load OR an invalid submission
            context = {
                'session': request.session,
                'path': request.path,
                'form': form,
                'title': 'library update',
                }

            return render_to_response('upload.html', RequestContext(request, context))

    else:
        # act; this is a confirmation
        plist = open(settings.TMP_XML_PATH)
        update_library(plist, dry_run=False)
        plist.close()

        return redirect('/')


class RequestForm(forms.Form):
    title = forms.CharField(required=False)
    artist = forms.CharField(required=False)
    show = forms.CharField(label="Source Anime", required=False)
    role = forms.CharField(label="Role (OP/ED/Insert/Character/etc.)", required=False)
    details = forms.CharField(widget=forms.Textarea, label="Additional Details", required=False)
    contact = forms.CharField(label="Twitter/Email/Whatever", required=False)

    def clean(self):
        cleaned_data = super(RequestForm, self).clean()

        passable = False
        for t in [cleaned_data[f] for f in cleaned_data]:
            if t:
                passable = True
                break

        if not passable:
            raise forms.ValidationError("I'm sure you can give us more information than that.")

        return cleaned_data

def request_addition(request):
    if 'q' in request.GET:
        d = {'title': request.GET['q']}
    else:
        d = {}

    form = RequestForm(initial=d)

    if request.method == 'POST':
        form = RequestForm(request.POST)
        if form.is_valid():
            f = form.cleaned_data
            ak_data = {
                    'user_ip': request.META['REMOTE_ADDR'],
                    'user_agent': request.META['HTTP_USER_AGENT'],
                    'referrer': request.META['HTTP_REFERER'],
                    'comment_author': f['contact'].encode('ascii', errors='ignore'),
                    }

            ascii_message = f['details'].encode('ascii', errors='ignore')

            spam = ak_api.comment_check(ascii_message, data=ak_data)

            if not spam:
                fields = ['%s:\n%s' % (r, f[r]) for r in f if f[r]]
                msg = MIMEText('\n\n'.join(fields), _charset="UTF-8")
                msg['Subject'] = '[nkd.su] %s' % f['title']
                msg['From'] = '"nkd.su" <nkdsu@bldm.us>'
                msg['To'] = settings.REQUEST_CURATOR

                sendmail(settings.REQUEST_CURATOR, msg.as_string())

                context = {'message': 'thank you for your request'}
            else:
                context = {'message': 'stop it with the spam'}

            return render_to_response('message.html', RequestContext(request, context))

    context = {
            'session': request.session,
            'path': request.path,
            'title': 'request an addition',
            'form': form,
            }

    return render_to_response('request.html', RequestContext(request, context))


def redirect_nicely(request):
    """ Redirect to ?from=, if present, otherwise redirect to / """
    if 'from' in request.GET:
        return redirect(request.GET['from'])
    else:
        return redirect('/')


def get_track_or_selection(request, track_id, wipe=True):
    """ Returns an iterable of tracks.

    If track_id is an actual track id, returns that track in a singleton tuple
    If track_id is 'selection', returns a QuerySet of all selected tracks
    If wipe is true, will clear the selection
    """
    if track_id == 'selection':
        tracks = Track.objects.filter(id__in=request.session['selection'])
        if wipe: request.session['selection'] = []
    else:
        tracks = (Track.objects.get(id=track_id),)


    return tracks

class BlockForm(forms.Form):
    """ Block something """
    reason = forms.CharField(max_length=256)

@login_required
def make_block(request, track_id):
    tracks = get_track_or_selection(request, track_id, wipe=False)

    if not tracks:
        context = {'message': 'nothing selected'}
        return render_to_response('message.html', RequestContext(request, context))

    if request.method == 'POST':
        form = BlockForm(request.POST)
        for track in tracks:
            if form.is_valid():
                block = Block(
                        track=track,
                        reason=form.cleaned_data['reason']
                        )
                block.save()

        # now is the time to wipe the selection
        if track_id == 'selection': request.session['selection'] = []
        return redirect('/')
    else:
        form = BlockForm()

    context = {
            'session': request.session,
            'path': request.path,
            'tracks': tracks,
            'form': form,
            'title': 'new block',
            }

    return render_to_response('block.html', RequestContext(request, context))

@login_required
def unblock(request, track_id):
    tracks = get_track_or_selection(request, track_id)
    week = Week()

    for track in tracks:
        block = week.block(track)
        if block:
            block.delete()

    return redirect_nicely(request)


def shortlist_or_discard(request, track_id, c=None):
    """ Shortlist or discard something, whichever class is passed to c """
    tracks = get_track_or_selection(request, track_id)

    for track in tracks:
        if c:
            # we should create an instance of c
            instance = c(track=track)
            try:
                instance.clean()
            except ValidationError:
                if len(tracks) == 1:
                    # don't bother if this is a multi-track operation
                    context = {'message': exc_info()[1].messages[0]}
                    return render_to_response('message.html', RequestContext(request, context))
            else:
                instance.save()
        else:
            # no class has been handed to us, so we should wipe the status of this track
            current = Week().shortlist_or_discard(track)
            if current:
                current.delete()

    return redirect_nicely(request)


@login_required
def shortlist(request, track_id):
    return shortlist_or_discard(request, track_id, Shortlist)

@login_required
def discard(request, track_id):
    return shortlist_or_discard(request, track_id, Discard)

@login_required
def unshortlist_or_undiscard(request, track_id):
    return shortlist_or_discard(request, track_id, None)


# javascript nonsense
def do_selection(request, select=True):
    """ Returns the current selection, optionally selects or deselects a track. """
    tracks = []

    if 'track_id[]' in request.POST:
        track_ids = dict(request.POST)[u'track_id[]'] # dicting is necessary for some reason
        tracks = Track.objects.filter(id__in=track_ids)

    elif 'track_id' in request.POST:
        track_id = request.POST['track_id']
        tracks = (Track.objects.get(id=track_id),)

    # take our current selection list and turn it into a set
    if 'selection' in request.session:
        selection = set(request.session['selection'])
    else:
        selection = set()

    altered = False
    for track in tracks:
        # add or remove, as necessary
        altered = True
        if select:
            selection.add(track.id)
            print track
        else:
            selection.remove(track.id)

    selection_queryset = Track.objects.filter(id__in=selection)

    # if our person is not authenticated, we have to be deselect things for them when they stop being eligible
    # or they might get pissed that their vote didn't work
    redacted = False
    if not request.user.is_authenticated():
        for track in selection_queryset:
            if track.ineligible():
                selection.remove(track.id)
                redacted = True

    # only write if necessary
    if redacted:
        selection_queryset = Track.objects.filter(id__in=selection)
    if redacted or altered:
        request.session['selection'] = list(selection)

    context = {
            'selection': selection_queryset,
            'vote_url': vote_url(selection_queryset),
            }

    if request.method == 'GET':
        return redirect_nicely(request)
    elif request.method == 'POST':
        return render_to_response('minitracklist.html', RequestContext(request, context))

def do_select(request):
    return do_selection(request, True)

def do_deselect(request):
    return do_selection(request, False)

def do_clear_selection(request):
    request.session['selection'] = []
    return do_selection(request)
