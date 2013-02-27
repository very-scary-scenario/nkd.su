# Create your views here.
# -*- coding: utf-8 -*-

from vote.models import (User, Track, Play, Block, Shortlist, ManualVote, Week,
                         latest_play, length_str, total_length, tweet_len,
                         tweet_url, Discard, vote_tweet)
from vote.forms import (RequestForm, SearchForm, LibraryUploadForm,
                        ManualVoteForm, BlockForm)
from vote.update_library import update_library
from vote.tasks import refresh
# we'll call refresh.delay() on pages that people might be looking for their
# votes on

from django.core.exceptions import ValidationError
from django.template import RequestContext
from django.http import Http404
from django.shortcuts import render_to_response, redirect
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.utils.http import urlquote
from django.core.paginator import Paginator
from django.core.mail import send_mail
from django.core.urlresolvers import reverse

from sys import exc_info
from datetime import datetime

import codecs
from markdown import markdown

import akismet

import tweepy

post_tw_auth = tweepy.OAuthHandler(settings.CONSUMER_KEY,
                                   settings.CONSUMER_SECRET)
post_tw_auth.set_access_token(settings.POSTING_ACCESS_TOKEN,
                              settings.POSTING_ACCESS_TOKEN_SECRET)
tw_api = tweepy.API(post_tw_auth)

ak_api = akismet.Akismet(key=settings.AKISMET_API_KEY,
                         blog_url=settings.AKISMET_BLOG_URL,
                         agent='nkdsu/0.0')


def summary(request, week=None):
    """
    Our landing page (as it looked at the end of week; manual weeks mostly for
    testing)
    """

    if not week:
        week = Week()

    form = SearchForm()

    unfiltered_tracklist = week.tracks_sorted_by_votes()

    if request.user.is_authenticated():
        tracklist = [t for t in unfiltered_tracklist if t.eligible()
                     and not week.shortlist_or_discard(t)]
        shortlist = week.shortlist()
        shortlist_len = length_str(total_length(shortlist))
        discard = week.discard()
        tracklist.extend([t for t in unfiltered_tracklist if t.ineligible()
                          and (t.ineligible() != 'played this week')
                          and not week.shortlist_or_discard(t)])
    else:
        shortlist = None
        discard = None
        shortlist_len = None
        tracklist = [t for t in unfiltered_tracklist if t.eligible()]
        tracklist.extend([t for t in unfiltered_tracklist if t.ineligible()
                          and (t.ineligible() != 'played this week')])

    tracklist_len = length_str(total_length(tracklist))

    # ditto plays
    playlist = [p.track for p in week.plays(invert=True)]
    for track in playlist:
        track._vote_week = week
        track._current_week = week

    if playlist:
        playlist_len = length_str(total_length(playlist))
    else:
        playlist_len = None

    context = {
        'week': week,
        'section': 'home',
        'session': request.session,
        'playlist': playlist,
        'form': form,
        'tracks': tracklist,
        'tracks_len': tracklist_len,
        'shortlist_len': shortlist_len,
        'shortlist': shortlist,
        'discard': discard,
        'playlist_len': playlist_len,
        'robot_apocalypse': week.prev().has_robot_apocalypse(),
    }

    render = render_to_response('index.html', RequestContext(request, context))
    return render


def roulette(request):
    """ Five random tracks """
    any_tracks = Track.objects.filter().order_by('?')

    if not request.user.is_authenticated():
        any_tracks = any_tracks.filter(hidden=False, inudesu=False)

    tracks = []
    pos = 0
    while len(tracks) < 5 and pos < len(any_tracks):
        track = any_tracks[pos]
        if track.eligible():
            tracks.append(track)
        pos += 1

    context = {
        'section': 'surprise me',
        'title': 'surprise me',
        'tracks': tracks,
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


def search_for_tracks(keywords, show_hidden=False):
    """Make a search that contains all of the keywords."""
    tracks = Track.objects.all()

    if not show_hidden:
        tracks = tracks.filter(hidden=False, inudesu=False)

    trackset = set(tracks)
    for keyword in keywords:
        trackset = {t for t in trackset
                    if keyword.lower() in t.canonical_string().lower()}
    return list(trackset)


def search_redirect(request):
    form = SearchForm(request.GET)

    if not form.is_valid():
        return redirect('/')
    else:
        query = form.cleaned_data['q']
        return redirect('/search/%s' % urlquote(query, safe=''))


def track(request, track_id, slug=None):
    """ A view of a single track """

    track = get_track_or_selection(request, track_id)[0]

    if not slug or slug != track.slug():
        return redirect(track.rel_url())

    if not request.META['SERVER_NAME'] == 'testserver':
        refresh.delay()

    context = {
        'added': Week(track.added).showtime,
        'path': request.path,
        'title': track.derived_title(),
        'track': track,
    }

    return render_to_response('track.html', RequestContext(request, context))


def search(request, query, pageno=1):
    query = query.replace('%2F', '/')

    try:
        trackset = (Track.objects.get(id=query),)
        if (not request.user.is_authenticated()) and trackset[0].hidden:
            trackset = []
    except Track.DoesNotExist:
        keyword_list = split_query_into_keywords(query)
        trackset = search_for_tracks(
            keyword_list, show_hidden=request.user.is_authenticated())

    paginator = Paginator(trackset, 20)
    page = paginator.page(pageno)

    context = {
        'title': query,
        'query': query,
        'tracks': page.object_list,
        'page': page,
    }

    return render_to_response('tracks.html', RequestContext(request, context))


def artist(request, artist):
    """ All tracks by a particular artist """
    artist_tracks = Track.objects.filter(
        id3_artist=artist).order_by('id3_title')

    if not request.user.is_authenticated():
        artist_tracks = artist_tracks.filter(hidden=False)

    if not artist_tracks:
        raise Http404

    context = {
        'title': artist.lower(),
        'tracks': artist_tracks,
    }

    return render_to_response('tracks.html', RequestContext(request, context))


def latest_show(request):
    """ Redirect to the last week's show """
    last_week = Week(ignore_apocalypse=True).prev()
    date_str = last_week.showtime.strftime('%d-%m-%Y')
    return redirect(reverse('show', kwargs={'date': date_str}))


def show(request, date):
    """ Playlist archive """
    day, month, year = (int(d) for d in date.split('-'))

    try:
        dart = timezone.make_aware(datetime(year, month, day),
                                   timezone.utc)
        week = Week(dart, correct=False, ignore_apocalypse=True)
    except ValueError:
        raise Http404

    plays = week.plays()

    if not plays or week.finish > timezone.now():
        raise Http404

    next_week = week.next()

    if next_week.finish < timezone.now() and next_week.has_plays():
        next_show = next_week.showtime
    else:
        next_show = None

    prev_week = week.prev()

    if prev_week.has_plays():
        prev_show = prev_week.showtime
    else:
        prev_show = None

    hours = []

    for play in plays:
        hour = play.datetime.hour
        if len(hours) == 0 or hours[-1].datetime.hour != hour:
            hours.append(play)

    playlist = []
    hour = 1
    for play in plays:
        if play in hours:
            playlist.append(hour)
            hour += 1
        playlist.append(play.track)

    this_week = Week()

    tracks = [t for t in playlist if type(t) != int]
    [setattr(t, '_vote_week', week) for t in tracks]
    [setattr(t, '_current_week', this_week) for t in tracks]
    tracks_len = length_str(total_length(tracks))

    tracks_added_this_week = len(week.added())

    context = {
        'week': week,
        'section': 'archive',
        'title': date,
        'this_show': week.showtime,
        'tracks': playlist,
        'tracks_len': tracks_len,
        'next_show': next_show,
        'prev_show': prev_show,
        'tracks_added_this_week': tracks_added_this_week,
    }

    return render_to_response('show.html', RequestContext(request, context))


def added(request, date=None):
    if date:
        day, month, year = (int(d) for d in date.split('-'))
        try:
            dart = timezone.make_aware(datetime(year, month, day),
                                       timezone.utc)
            week = Week(dart)
        except ValueError:
            raise Http404
    else:
        week = Week(Track.objects.all().order_by('-added')[0].added)
        return redirect('/added/%s/' % week.showtime.strftime('%d-%m-%Y'))

    tracks = week.added(show_hidden=request.user.is_authenticated())

    # set up prev/next buttons
    next_week_with_additions = prev_week_with_additions = None

    older_tracks = Track.objects.filter(added__lt=week.start,
                                        hidden=False).order_by('-added')
    newer_tracks = Track.objects.filter(added__gt=week.finish,
                                        hidden=False).order_by('added')

    if older_tracks:
        prev_week_with_additions = Week(older_tracks[0].added).showtime
    if newer_tracks:
        next_week_with_additions = Week(newer_tracks[0].added).showtime

    plays_this_week = bool(week.plays())

    context = {
        'title': 'new tracks from %s' % date,
        'section': 'new tracks',
        'additions_from': week.showtime,
        'tracks': tracks,
        'next_week_with_additions': next_week_with_additions,
        'prev_week_with_additions': prev_week_with_additions,
        'plays_this_week': plays_this_week,
        'is_current_week': week == Week(),
    }

    return render_to_response('tracks.html', RequestContext(request, context))


def info(request):
    return docs(request, 'what?', 'README.md')


def api_docs(request):
    return docs(request, 'api', 'API.md')


def docs(request, title, filename):
    words = markdown(codecs.open(settings.SITE_ROOT + filename,
                                 encoding='utf-8').read())
    context = {
        'title': title,
        'words': words,
    }

    return render_to_response('markdown.html', RequestContext(request,
                                                              context))


def confirm(request, action, deets=None):
    context = {
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

    play = Play(datetime=timezone.now(), track=track)

    try:
        play.clean()
    except ValidationError:
        context = {'message': exc_info()[1].messages[0]}
        return render_to_response('message.html',
                                  RequestContext(request, context))

    else:
        if not ('confirm' in request.GET and request.GET['confirm'] == 'true'):
            return confirm(request, 'mark %s as played'
                           % track.derived_title())
        else:
            # tweet it
            canon = track.canonical_string()
            if len(canon) > 140 - (len(settings.HASHTAG) + 1):
                canon = canon[0:140-(len(settings.HASHTAG)+2)]+u'…'
            status = u'%s %s' % (canon, settings.HASHTAG)

            try:
                tweet = tw_api.update_status(status)
            except tweepy.TweepError as e:
                tweet_sent = False
                error = e
            else:
                tweet_sent = True

            if tweet_sent:
                play.tweet_id = tweet.id
                print play.tweet_id
            else:
                context = {
                    'message': 'the tweet failed to send',
                    'deets': '<p>the play has been added anyway</p><p>you '
                    'should <a href="https://twitter.com/intent/tweet?text='
                    '%s">send the now playing tweet manually</a></p><p>error: '
                    '%s</p>' % (urlquote(status), error),
                    'safe': True
                }

            play.save()
            # unshortlist/discard
            shortlist_or_discard(request, track.id)

            if not tweet_sent:
                return render_to_response('message.html',
                                          RequestContext(request, context))

    return redirect_nicely(request)


@login_required
def unmark_as_played(request, track_id):
    """ Deletes the latest Play for a track """
    try:
        track = Track.objects.get(id=track_id)
    except Track.DoesNotExist:
        raise Http404

    try:
        play = latest_play(track)
    except IndexError:
        raise Http404

    if not ('confirm' in request.GET and request.GET['confirm'] == 'true'):
        return confirm(request, 'unmark %s as played' % track.derived_title())
    else:
        try:
            tw_api.destroy_status(id=play.tweet_id)
        except:
            pass

        play.delete()
        return redirect_nicely(request)


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
            changes = update_library(
                f, dry_run=True,
                is_inudesu=form.cleaned_data['inudesu'])

            request.session['inudesu'] = form.cleaned_data['inudesu']

            if changes:
                summary = '\n'.join(changes)
            else:
                summary = 'no changes'
            response = confirm(request, 'update the library', summary)
            f.close()

            return response

    elif ((not ('confirm' in request.GET and request.GET['confirm'] == 'true'))
          or (request.method == 'POST' and not form.is_valid())):
        # this is an initial load OR an invalid submission
        context = {
            'form': form,
            'title': 'library update',
        }

        return render_to_response('upload.html', RequestContext(request,
                                                                context))

    else:
        # act; this is a confirmation
        plist = open(settings.TMP_XML_PATH)
        print request.session['inudesu']
        update_library(
            plist, dry_run=False,
            is_inudesu=request.session['inudesu'])

        plist.close()

        if request.session['inudesu']:
            return redirect('/inudesu/')
        else:
            return redirect('/hidden/')


def request_addition(request):
    if 'q' in request.GET:
        d = {'title': request.GET['q']}
    else:
        d = {}

    form = RequestForm(initial=d)

    if request.method == 'POST':
        form = RequestForm(request.POST)

        if form.is_valid():
            # akismet check
            f = form.cleaned_data
            ak_data = {
                'user_ip': request.META['REMOTE_ADDR'],
                'user_agent': request.META['HTTP_USER_AGENT'],
                'referrer': request.META['HTTP_REFERER'],
                'comment_author': f['contact'].encode('ascii',
                                                      errors='ignore'),
            }

            ascii_message = f['details'].encode('ascii', errors='ignore')

            # get the boolean response from akismet
            spam = ak_api.comment_check(ascii_message, data=ak_data)

            if not spam:
                fields = ['%s:\n%s' % (r, f[r]) for r in f if f[r]]

                send_mail(
                    '[nkd.su] %s' % f['title'],
                    '\n\n'.join(fields),
                    '"nkd.su" <nkdsu@bldm.us>',
                    [settings.REQUEST_CURATOR],
                )

                context = {'message': 'thank you for your request'}
            else:
                context = {'message': 'stop it with the spam'}

            return render_to_response('message.html', RequestContext(request,
                                                                     context))

    context = {
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
        if wipe:
            request.session['selection'] = []
    else:
        tracks = (Track.objects.get(id=track_id),)

    return tracks


@login_required
def make_block(request, track_id):
    tracks = get_track_or_selection(request, track_id, wipe=False)

    if not tracks:
        context = {'message': 'nothing selected'}
        return render_to_response('message.html', RequestContext(request,
                                                                 context))

    if request.method == 'POST':
        form = BlockForm(request.POST)
        for track in tracks:
            if form.is_valid():
                block = Block(
                    track=track,
                    reason=form.cleaned_data['reason'])
                block.save()

        # now is the time to wipe the selection
        if track_id == 'selection':
            request.session['selection'] = []

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
        block = track.block(week)
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
                    return render_to_response('message.html',
                                              RequestContext(request, context))
            else:
                instance.save()
        else:
            # no class has been handed to us, so we should wipe the status of
            # this track
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


def hide_or_unhide(request, track_id, hidden):
    tracks = get_track_or_selection(request, track_id)
    for track in tracks:
        track.hidden = hidden
        track.save()
    return redirect_nicely(request)


@login_required
def hide(request, track_id):
    return hide_or_unhide(request, track_id, True)


@login_required
def unhide(request, track_id):
    return hide_or_unhide(request, track_id, False)


@login_required
def hidden(request):
    """ A view of all currently hidden tracks """
    context = {
        'session': request.session,
        'path': request.path,
        'title': 'hidden tracks',
        'tracks': Track.objects.filter(hidden=True, inudesu=False),
        'path': request.path,
    }

    return render_to_response('tracks.html', RequestContext(request, context))


@login_required
def inudesu(request):
    """ A view of unhidden inudesu tracks """
    context = {
        'session': request.session,
        'path': request.path,
        'title': 'inu desu',
        'tracks': Track.objects.filter(hidden=False, inudesu=True),
        'path': request.path,
    }

    return render_to_response('tracks.html', RequestContext(request, context))


def increment(dictionary, key):
    """ Increment by one or create a value of 1 in a dictionary. """
    try:
        dictionary[key] += 1
    except KeyError:
        dictionary[key] = 1


def top(dictionary):
    """
    Return a sorted tuple of (key, value) for the top values in a dictionary
    """

    l = sorted(dictionary, key=lambda t: dictionary[t], reverse=True)
    return [(t, dictionary[t]) for t in l]


def make_relative(absolute, reference):
    """ Return a dictionary of ratios of absolute[x]:reference[x] """
    ratios = {}
    for key in absolute:
        ratios[key] = float(absolute[key]) / float(reference[key])

    for key in [k for k in absolute if k not in reference]:
        ratios[key] = 0

    return ratios


def useful(the_list, convert_to_percent=False):
    """ Convert a list of (user_id, key) tuples into (<User>, key) tuples.
    If convert_to_percent is True, multiply all keys by 100 """
    new_list = []
    for user_id, value in the_list:
        if convert_to_percent:
            value *= 100
            value = '%i%%' % value

        new_list.append((User(user_id), value))

    return new_list


def get_stats():
    # how big should our top lists be?
    top_count = 10

    # create our stat dictionaries using tracks as keys...
    track_votes = {}

    # and using twitter user IDs as keys...
    user_denials = {}
    user_successes = {}
    user_votes = {}
    user_weeks = {}  # the number of weeks a user has participated
    weeks_since_user_voted = {}

    week = Week()
    # roll back until we're at a week that there was a show on
    while not week.has_plays():
        week = week.prev()

    weeks = []

    weeks_before_now = 1

    # iterate through weeks, getting information on each
    while week.has_plays():
        weeks.append(week)

        users = set()

        # in this case, we don't care about manual votes, so we use
        # week._votes()
        for vote in week._votes():
            if vote.get_tracks().exists():
                users.add(vote.user_id)
            for track in vote.get_tracks():
                increment(track_votes, track)
                increment(user_votes, vote.user_id)

                if track in week.tracks_played():
                    increment(user_successes, vote.user_id)
                else:
                    increment(user_denials, vote.user_id)

        for user in users:
            increment(user_weeks, user)

            if user not in weeks_since_user_voted:
                weeks_since_user_voted[user] = weeks_before_now

        week = week.prev()
        weeks_before_now += 1

    unfiltered_user_success_ratios = top(
        make_relative(user_successes, user_votes))

    # if a person hasn't voted on at least three seperate weeks and at some
    # point in the last month, they're not worth considering
    user_success_ratios = [u for u in unfiltered_user_success_ratios
                           if user_weeks[u[0]] >= 3
                           and weeks_since_user_voted[u[0]] <= 4]

    most_successful_users = useful(user_success_ratios[:top_count],
                                   convert_to_percent=True)
    least_successful_users = useful(list(reversed(
        user_success_ratios))[:top_count], convert_to_percent=True)

    return (
        {'type': 'user_stats', 'items': (
            {
                'name': 'most successful users',
                'stats': most_successful_users,
                'heading': 'batting average',
            },
            {
                'name': 'least successful users',
                'stats': least_successful_users,
                'heading': 'batting average',
            },
            {
                'name': 'most obsessive users',
                'stats': useful(top(user_weeks)[:top_count]),
                'heading': 'weeks voted',
            },
        ),
        },

        {'type': 'track_stats', 'items': (
            {
                'name': 'most popular tracks',
                'stats': top(track_votes)[:top_count],
                'heading': 'votes',
            },
        ),
        },
    )


def stats(request):
    current_week = Week()
    context = {
        'stats': get_stats,
        'week': current_week,
        'section': 'stats',
        'title': 'stats',
    }

    return render_to_response('stats.html', RequestContext(request, context))


# javascript nonsense
def do_selection(request, select=True):
    """
    Returns the current selection, optionally selects or deselects a track.
    """

    tracks = []

    if 'track_id[]' in request.POST:
        track_ids = dict(request.POST)[u'track_id[]']
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
        else:
            try:
                selection.remove(track.id)
            except KeyError:
                # already not selected
                pass

    selection_queryset = Track.objects.filter(id__in=selection)

    # if our person is not authenticated, we have to be deselect things for
    # them when they stop being eligible or they might get pissed that their
    # vote didn't work
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

    tweet = vote_tweet(selection_queryset)
    vote_url = tweet_url(tweet)
    selection_len = length_str(total_length(selection_queryset))

    context = {
        'selection': selection_queryset,
        'vote_url': vote_url,
        'selection_len': selection_len,
        'tweet_is_too_long': tweet_len(tweet) > 140,
    }

    if request.method == 'GET':
        return redirect_nicely(request)
    elif request.method == 'POST':
        return render_to_response('minitracklist.html',
                                  RequestContext(request, context))


def do_select(request):
    return do_selection(request, True)


def do_deselect(request):
    return do_selection(request, False)


def do_clear_selection(request):
    request.session['selection'] = []
    return do_selection(request)
