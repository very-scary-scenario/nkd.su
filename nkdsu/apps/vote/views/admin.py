# coding: utf-8

import plistlib

from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse, reverse_lazy
from django.http import HttpResponse
from django.shortcuts import redirect, get_object_or_404
from django.utils import timezone
from django.views.generic import (DetailView, CreateView, View, FormView,
                                  TemplateView, ListView)
from django.views.generic.base import TemplateResponseMixin

from ..forms import LibraryUploadForm, NoteForm
from ..models import Track, Vote, Block, Show, TwitterUser, Request, Note
from ..update_library import update_library
from .js import JSApiMixin


class AdminMixin(object):
    """
    A mixin we should apply to all admin views.
    """

    @classmethod
    def as_view(cls):
        return login_required(super(AdminMixin, cls).as_view())


class TrackSpecificAdminMixin(AdminMixin):
    def get_track(self):
        return get_object_or_404(Track, pk=self.kwargs['pk'])

    def get_context_data(self, *args, **kwargs):
        context = super(TrackSpecificAdminMixin, self
                        ).get_context_data(*args, **kwargs)
        context['track'] = self.get_track()
        return context


class AdminActionMixin(AdminMixin):
    url = reverse_lazy('vote:index')

    def get_redirect_url(self):
        referer = self.request.META.get('HTTP_REFERER')
        next_param = self.request.GET.get('next')

        if next_param is not None:
            self.url = next_param
        elif referer is not None:
            self.url = referer

        return self.url

    def do_thing_and_redirect(self):
        self.do_thing()
        return redirect(self.get_redirect_url())


class AdminAction(AdminActionMixin):
    """
    A view for an admin action that we can be comfortable doing immediately.
    """

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
        self.request = request
        if request.GET.get('confirm') == 'true':
            return self.do_thing_and_redirect()
        else:
            return super(DestructiveAdminAction, self).get(request, *args,
                                                           **kwargs)


class SelectionAdminAction(AdminAction, View):
    """
    Do something with the current selection and wipe it.
    """

    model = Track

    def get_queryset(self):
        pks = self.request.session['selection'] or []
        return self.model.objects.filter(pk__in=pks)

    def do_thing_and_redirect(self):
        # we only want to clear the selection if the rest of this process is
        # successful, or shillito will get understandably mad
        resp = super(SelectionAdminAction, self).do_thing_and_redirect()
        self.request.session['selection'] = []
        return resp


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

        if not track.revealed:
            track.revealed = timezone.now()

        track.save()


class ManualVote(TrackSpecificAdminMixin, CreateView):
    model = Vote
    fields = ['text', 'name', 'kind']
    template_name = 'manual_vote.html'

    def form_valid(self, form):
        track = self.get_track()
        vote = form.save(commit=False)
        vote.date = timezone.now()
        vote.save()
        vote.tracks.add(track)
        vote.save()
        return redirect(reverse('vote:index'))


class MakeBlock(TrackSpecificAdminMixin, CreateView):
    model = Block
    fields = ['reason']
    template_name = 'block.html'

    def form_valid(self, form):
        block = form.save(commit=False)
        block.track = self.get_track()
        block.show = Show.current()
        block.save()
        return redirect(reverse('vote:index'))


class Unblock(AdminAction, DetailView):
    model = Track

    def do_thing(self):
        block = get_object_or_404(Block, track=self.get_object(),
                                  show=Show.current())
        block.delete()


class MakeBlockWithReason(AdminAction, DetailView):
    model = Track

    def do_thing(self):
        Block(
            reason=self.request.GET.get('reason'),
            track=self.get_object(),
            show=Show.current(),
        ).save()


class MakeShortlist(AdminAction, DetailView):
    model = Track

    def do_thing(self):
        self.get_object().shortlist()


class MakeDiscard(AdminAction, DetailView):
    model = Track

    def do_thing(self):
        self.get_object().discard()


class OrderShortlist(AdminMixin, JSApiMixin, View):
    def do_thing(self, post):
        current = Show.current()
        indescriminate_shortlist = current.shortlist_set.all()
        shortlisted = current.shortlisted()
        pks = post.getlist('shortlist[]')

        min_placeholder_index = max([s.index for s in
                                     indescriminate_shortlist]) + 1

        if set(pks) != set([t.pk for t in shortlisted]):
            return HttpResponse('reload')

        # delete shortlists that have been played
        indescriminate_shortlist.exclude(track__in=shortlisted).filter(
            track__in=current.playlist()
        ).delete()

        for delta in [min_placeholder_index, 0]:
            for index, pk in enumerate(pks):
                shortlist = indescriminate_shortlist.get(track__pk=pk)
                shortlist.index = index + delta
                shortlist.save()


class ResetShortlistAndDiscard(AdminAction, DetailView):
    model = Track

    def do_thing(self):
        self.get_object().reset_shortlist_discard()


class LibraryUploadView(AdminMixin, FormView):
    template_name = 'upload.html'
    form_class = LibraryUploadForm

    def form_valid(self, form):
        self.request.session['library_update'] = {
            'inudesu': form.cleaned_data['inudesu'],
            'library_xml': form.cleaned_data['library_xml'].read(),
        }

        return redirect(reverse('vote:admin:confirm_upload'))


class LibraryUploadConfirmView(DestructiveAdminAction, TemplateView):
    """
    Update the library.
    """

    def update_library(self, dry_run):
        library_update = self.request.session['library_update']
        return update_library(
            plistlib.readPlistFromString(
                library_update['library_xml'].encode('utf-8')),
            inudesu=library_update['inudesu'],
            dry_run=dry_run,
        )

    def get_deets(self):
        return '\n\n'.join(self.update_library(dry_run=True))

    def do_thing(self):
        return self.update_library(dry_run=False)


class ToggleAbuser(AdminAction, DetailView):
    model = TwitterUser

    def get_object(self):
        return self.model.objects.get(user_id=self.kwargs['user_id'])

    def do_thing(self):
        user = self.get_object()
        user.is_abuser = not user.is_abuser
        user.save()


class HiddenTracks(AdminMixin, ListView):
    model = Track
    template_name = 'hidden.html'
    context_object_name = 'tracks'

    def get_queryset(self):
        return self.model.objects.filter(hidden=True, inudesu=False)


class InuDesuTracks(AdminMixin, ListView):
    model = Track
    template_name = 'inudesu.html'
    context_object_name = 'tracks'

    def get_queryset(self):
        return self.model.objects.filter(hidden=False, inudesu=True)


class BadTrivia(AdminMixin, ListView):
    model = Request
    template_name = 'trivia.html'
    context_object_name = 'requests'

    def get_queryset(self):
        return self.model.objects.all().order_by('-created')


class ShortlistSelection(SelectionAdminAction):
    def do_thing(self):
        for track in self.get_queryset():
            track.shortlist()


class DiscardSelection(SelectionAdminAction):
    def do_thing(self):
        for track in self.get_queryset():
            track.discard()


class ResetShortlistAndDiscardSelection(SelectionAdminAction):
    def do_thing(self):
        for track in self.get_queryset():
            track.reset_shortlist_discard()


class MakeNote(TrackSpecificAdminMixin, FormView):
    template_name = 'note.html'
    form_class = NoteForm

    def form_valid(self, form):
        note = form.save(commit=False)
        note.track = self.get_track()

        if form.cleaned_data['just_for_current_show']:
            note.show = Show.current()

        note.save()
        return redirect(reverse('vote:index'))


class RemoveNote(DestructiveAdminAction, DetailView):
    """
    Remove this note.
    """

    model = Note

    def get_deets(self):
        obj = self.get_object()

        print self.get_redirect_url()

        return '"{content}"; {track}'.format(
            track=obj.track,
            content=obj.content,
        )

    def do_thing(self):
        self.get_object().delete()
