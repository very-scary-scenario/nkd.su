# coding: utf-8

from sys import exc_info

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse_lazy
from django.http import Http404, HttpResponse
from django.shortcuts import redirect
from django.utils.http import urlquote
from django.views.generic import DetailView
from django.views.generic.base import TemplateResponseMixin

from ..forms import LibraryUploadForm, ManualVoteForm, BlockForm
from ..models import Track
from ..update_library import update_library


class AdminMixin(object):
    """
    A mixin we should apply to all admin views.
    """

    @classmethod
    def as_view(cls):
        return login_required(super(AdminMixin, cls).as_view())


class AdminActionMixin(AdminMixin):
    url = reverse_lazy('vote:index')

    def get_redirect_url(self):
        return self.url

    def do_thing_and_redirect(self):
        self.do_thing()
        return redirect(self.get_redirect_url())


class AdminAction(AdminActionMixin):
    """
    A view for an admin action that we can be comfortable doing immediately.
    """

    def get_redirect_url(self):
        referer = self.request.META.get('HTTP_REFERER')
        next_param = self.request.GET.get('next')

        if next_param is not None:
            self.url = next_param
        elif referer is not None:
            self.url = referer

        else:
            return super(AdminAction, self).get_redirect_url()

    def get(self, request, *args, **kwargs):
        return self.do_thing_and_redirect()


class DestructiveAdminAction(AdminActionMixin, TemplateResponseMixin):
    """
    A view for an admin action that's worth asking if our host is sure.
    """

    template_name = 'confirm.html'
    deets = None

    def get_deets(self):
        return self.deets

    def get_context_data(self, *args, **kwargs):
        context = super(DestructiveAdminAction, self
                        ).get_context_data(*args, **kwargs)

        context.update({
            'deets': self.get_deets(),
            'action': self.__doc__.strip('\n .'),
            'next': self.request.META.get('HTTP_REFERER'),
        })
        return context

    def get(self, request, *args, **kwargs):
        if request.GET.get('confirm') == 'true':
            return self.do_thing_and_redirect()
        else:
            return super(DestructiveAdminAction, self).get(request, *args,
                                                           **kwargs)


class Play(DestructiveAdminAction, DetailView):
    """
    Mark this track as played.
    """

    model = Track

    def get_deets(self):
        return unicode(self.get_object())

    def do_thing(self):
        self.get_object().play()


class Hide(AdminAction, DetailView):
    model = Track

    def do_thing(self):
        track = self.get_object()
        track.hidden = True
        track.save()


class Unhide(AdminAction, DetailView):
    model = Track

    def do_thing(self):
        track = self.get_object()
        track.hidden = False
        track.save()


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
            canon = track.get_absolute_url()
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
