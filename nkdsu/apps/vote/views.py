# -*- coding: utf-8 -*-

import codecs
from sys import exc_info
from datetime import datetime
from random import choice

import tweepy
from markdown import markdown

from django.core.exceptions import ValidationError
from django.template import RequestContext
from django.shortcuts import get_object_or_404
from django.http import Http404, HttpResponse
from django.shortcuts import render_to_response, redirect
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.utils.http import urlquote
from django.core.paginator import Paginator
from django.core.mail import send_mail
from django.views.generic import TemplateView, ListView

from .forms import (RequestForm, SearchForm, LibraryUploadForm,
                    ManualVoteForm, BlockForm, BadMetadataForm)
from .update_library import update_library
from ..vote import trivia, mixins
from ..vote.models import Show


post_tw_auth = tweepy.OAuthHandler(settings.CONSUMER_KEY,
                                   settings.CONSUMER_SECRET)
post_tw_auth.set_access_token(settings.POSTING_ACCESS_TOKEN,
                              settings.POSTING_ACCESS_TOKEN_SECRET)
tw_api = tweepy.API(post_tw_auth)


class IndexView(mixins.CurrentShowMixin, TemplateView):
    template_name = 'index.html'


class Archive(ListView):
    template_name = 'archive.html'

    def get_queryset(self):
        qs = Show.objects.filter(end__lt=timezone.now())
        return qs.order_by('-showtime')


class ShowDetail(mixins.ShowDetail):
    template_name = 'show_detail.html'


def roulette(request, mode=None):
    """ Five random tracks """
    if mode is None:
        any_tracks = Track.objects.filter()
    else:
        any_tracks = Track.objects.filter(play=None)

    if not request.user.is_authenticated():
        any_tracks = any_tracks.filter(hidden=False, inudesu=False)

    any_tracks = any_tracks.order_by('?')

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
        'mode': mode,
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

    context = {
        'added': Week(track.added).showtime,
        'title': track.derived_title(),
        'track': track,
    }

    return render_to_response('track.html', RequestContext(request, context))


def user(request, screen_name):
    """ Shrines """

    user = User(screen_name)

    try:
        user.name()
    except IndexError:
        raise Http404

    context = {
        'voter': user,
        'no_select': True,
    }

    return render_to_response('user.html', RequestContext(request, context))


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
        artist_tracks = artist_tracks.filter(hidden=False, inudesu=False)

    if not artist_tracks.exists():
        raise Http404

    context = {
        'title': artist.lower(),
        'tracks': artist_tracks,
    }

    return render_to_response('tracks.html', RequestContext(request, context))


def latest_show(request):
    """ Redirect to the last week's show """
    last_week = Week(ignore_apocalypse=True).prev()
    return redirect(last_week.get_absolute_url())


def show(request, date):
    """ Playlist archive """
    year, month, day = (int(d) for d in date.split('-'))
    if day > 31:
        old_date = True
        day, month, year = (int(d) for d in date.split('-'))
    else:
        old_date = False

    try:
        dart = timezone.make_aware(datetime(year, month, day),
                                   timezone.utc)
        week = Week(dart, correct=False, ignore_apocalypse=True)
    except ValueError:
        raise Http404

    if old_date:
        return redirect(week.get_absolute_url())

    plays = week.plays()

    if not plays:
        if week.finish > timezone.now():
            return redirect('/')
        else:
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
        year, month, day = (int(d) for d in date.split('-'))
        if day > 31:
            old_date = True
            day, month, year = (int(d) for d in date.split('-'))
        else:
            old_date = False

        try:
            dart = timezone.make_aware(datetime(year, month, day),
                                       timezone.utc)
            week = Week(dart)
        except ValueError:
            raise Http404

        if old_date:
            return redirect(week.get_added_url())
    else:
        week = Week(Track.objects.all().order_by('-added')[0].added)
        return redirect(week.get_added_url())

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
        'no_select': True,
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
            if track.inudesu:
                hashtag = settings.INUDESU_HASHTAG
            else:
                hashtag = settings.HASHTAG

            if len(canon) > 140 - (len(hashtag) + 1):
                canon = canon[0:140-(len(hashtag)+2)]+u'…'

            status = u'%s %s' % (canon, hashtag)

            try:
                tweet = tw_api.update_status(status)
            except tweepy.TweepError as e:
                tweet_sent = False
                error = e
            else:
                tweet_sent = True

            if tweet_sent:
                play.tweet_id = tweet.id
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
        update_library(
            plist, dry_run=False,
            is_inudesu=request.session['inudesu'])

        plist.close()

        if request.session['inudesu']:
            return redirect('/inudesu/')
        else:
            return redirect('/hidden/')


def report_bad_metadata(request, track_id):
    track = Track.objects.get(id=track_id)

    question = choice(trivia.questions.keys())
    d = {'trivia_question': question, 'track_id': track_id}

    if request.method == 'POST':
        form = BadMetadataForm(request.POST)
    else:
        form = BadMetadataForm(initial=d)

    if request.method == 'POST':
        if form.is_valid():
            f = form.cleaned_data

            fields = ['%s:\n%s' % (r, f[r]) for r in f if f[r]]
            fields.append(track.url())

            send_mail(
                '[nkd.su report] %s' % track.canonical_string(),
                '\n\n'.join(fields),
                '"nkd.su" <nkdsu@bldm.us>',
                [settings.REQUEST_CURATOR],
            )

            context = {'message': 'thanks for letting us know'}

            return render_to_response('message.html',
                                      RequestContext(request, context))

    form.fields['trivia'].label = 'Captcha: %s' % question
    form.data['trivia'] = ''
    form.data['trivia_question'] = question

    context = {
        'title': 'report bad metadata',
        'track': track,
        'form': form,
        'no_select': True,
    }

    return render_to_response('report.html', RequestContext(request, context))


def request_addition(request):
    question = choice(trivia.questions.keys())
    d = {'trivia_question': question}

    if 'q' in request.GET:
        d['title'] = request.GET['q']

    if request.method == 'POST':
        form = RequestForm(request.POST)
    else:
        form = RequestForm(initial=d)

    if request.method == 'POST':
        if form.is_valid():
            f = form.cleaned_data

            fields = ['%s:\n%s' % (r, f[r]) for r in f if f[r]]

            send_mail(
                '[nkd.su] %s' % f['title'],
                '\n\n'.join(fields),
                '"nkd.su" <nkdsu@bldm.us>',
                [settings.REQUEST_CURATOR],
            )

            context = {'message': 'thank you for your request'}

            return render_to_response('message.html',
                                      RequestContext(request, context))

    form.fields['trivia'].label = 'Captcha: %s' % question
    form.data['trivia'] = ''
    form.data['trivia_question'] = question

    context = {
        'title': 'request an addition',
        'form': form,
        'no_select': True,
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
        tracks = get_object_or_404(Track, id=track_id),

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
        'tracks': tracks,
        'form': form,
        'title': 'new block',
    }

    return render_to_response('block.html', RequestContext(request, context))


@login_required
def make_block_with_reason(request, track_id):
    """
    Block a track for a GET-defined reason.
    """

    tracks = get_track_or_selection(request, track_id, wipe=False)
    reason = request.GET.get('reason', None)

    if reason is None:
        raise Http404

    for track in tracks:
        Block(track=track, reason=reason).save()

    return redirect('/')


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
def shortlist_order(request):
    id_order = request.GET.getlist('shortlist[]')
    week = Week()

    for index, the_id in enumerate(id_order):
        track = Track.objects.get(id=the_id)
        shortlist = week.shortlist(track=track)
        shortlist.index = index
        shortlist.save()

    return HttpResponse('cool')


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
def toggle_abuse(request, user_id):
    our_abuser = Abuser.objects.filter(user_id=user_id)

    if our_abuser.exists():
        our_abuser.delete()
    else:
        Abuser(user_id=user_id).save()

    user = User(user_id)

    return redirect(user.get_absolute_url())


@login_required
def hidden(request):
    """ A view of all currently hidden tracks """
    context = {
        'session': request.session,
        'title': 'hidden tracks',
        'tracks': Track.objects.filter(hidden=True, inudesu=False),
    }

    return render_to_response('tracks.html', RequestContext(request, context))


@login_required
def inudesu(request):
    """ A view of unhidden inudesu tracks """
    context = {
        'session': request.session,
        'title': 'inu desu',
        'tracks': Track.objects.filter(hidden=False, inudesu=True),
    }

    return render_to_response('tracks.html', RequestContext(request, context))


@login_required
def bad_trivia(request):
    """ Incorrect trivia """
    context = {
        'title': 'the worst trivia',
        'requests': Request.objects.all().order_by('-created'),
        'no_select': True
    }

    return render_to_response('trivia.html', RequestContext(request, context))


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
    user_streak_lengths = {}

    week = Week()
    # roll back until we're at a week that there was a show on
    while not week.has_plays():
        week = week.prev()

    weeks = []

    # make a list of weeks
    while week.has_plays():
        weeks.append(week)
        week = week.prev()

    for depth, week in enumerate(weeks, start=1):
        users_that_voted = set()

        # in this case, we don't care about manual votes, so we use
        # week._votes()
        for vote in week._votes():
            if vote.get_tracks().exists():
                users_that_voted.add(vote.user_id)

            if depth < 26:  # we don't care about most stats older than this
                for track in vote.get_tracks():
                    increment(track_votes, track)
                    increment(user_votes, vote.user_id)

                    if track in week.tracks_played():
                        increment(user_successes, vote.user_id)
                    else:
                        increment(user_denials, vote.user_id)

                for user in users_that_voted:
                    increment(user_weeks, user)

                    if user not in weeks_since_user_voted:
                        weeks_since_user_voted[user] = depth

        if depth == 1:
            user_streaks_running = set(users_that_voted)

        for user in list(user_streaks_running):
            if not user in users_that_voted:
                user_streak_lengths[user] = depth
                user_streaks_running.remove(user)

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
                'stats': useful(top(user_streak_lengths)[:top_count]),
                'heading': 'current streak',
                'unlimited': True,
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
        'no_select': True,
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

    return HttpResponse()  # XXX

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
