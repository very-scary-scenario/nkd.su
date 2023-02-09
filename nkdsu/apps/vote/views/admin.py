import os
import plistlib
from typing import Any

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import ValidationError
from django.forms import Form
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import (
    CreateView,
    DetailView,
    FormView,
    ListView,
    TemplateView,
    View,
)
from django.views.generic.base import TemplateResponseMixin

from nkdsu.views import AnyLoggedInUserMixin
from .js import JSApiMixin
from ..forms import CheckMetadataForm, LibraryUploadForm, NoteForm
from ..models import Block, Note, Request, Show, Track, TwitterUser, Vote
from ..update_library import metadata_consistency_checks, update_library


class ElfMixin(AnyLoggedInUserMixin):
    """
    A mixin for views that only elfs (or staff) can see.
    """

    @classmethod
    def as_view(cls, **kw):
        from ..templatetags.vote_tags import is_elf
        return user_passes_test(is_elf)(super().as_view(**kw))


class AdminMixin(AnyLoggedInUserMixin):
    """
    A mixin we should apply to all admin views.
    """

    def handle_validation_error(self, error):
        context = {
            'action': self.__doc__.strip('\n .'),
            'error': error.error_dict,
        }
        return TemplateResponse(self.request, 'admin_error.html', context)

    @classmethod
    def as_view(cls, **kw):
        return user_passes_test(lambda u: u.is_staff)(super().as_view(**kw))


class TrackSpecificAdminMixin(AdminMixin):
    def get_track(self):
        return get_object_or_404(Track, pk=self.kwargs['pk'])

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
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

    def get_ajax_success_message(self):
        self.object = self.get_object()
        context = self.get_context_data()
        context.update(
            {
                'track': self.object,
                'cache_invalidator': os.urandom(16),
            }
        )
        return TemplateResponse(
            self.request,
            'include/track.html',
            context,
        )

    def do_thing_and_redirect(self):
        try:
            self.do_thing()
        except ValidationError as e:
            return self.handle_validation_error(e)
        else:
            if self.request.GET.get('ajax'):
                return self.get_ajax_success_message()
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

    def get_cancel_url(self):
        referer = self.request.META.get('HTTP_REFERER')
        if referer:
            cancel_url = referer
        else:
            cancel_url = reverse('vote:index')

        return cancel_url

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        context.update(
            {
                'deets': self.get_deets(),
                'action': self.__doc__.strip('\n .'),
                'cancel_url': self.get_cancel_url(),
            }
        )
        return context

    def get(self, request, *args, **kwargs):
        self.request = request
        if request.GET.get('confirm') == 'true':
            return self.do_thing_and_redirect()
        else:
            return super().get(request, *args, **kwargs)


class SelectionAdminAction(AdminAction, View):
    """
    Do something with the current selection and wipe it.
    """

    model = Track
    fmt = u'{} modified'

    def get_queryset(self):
        pks = self.request.session['selection'] or []
        return self.model.objects.filter(pk__in=pks)

    def do_thing_and_redirect(self):
        # we only want to clear the selection if the rest of this process is
        # successful, or shillito will get understandably mad
        resp = super().do_thing_and_redirect()

        count = self.get_queryset().count()
        tracks = (u'{} track' if count == 1 else u'{} tracks').format(count)
        messages.success(self.request, self.fmt.format(tracks))

        self.request.session['selection'] = []
        return resp


class Play(DestructiveAdminAction, DetailView):
    """
    Mark this track as played.
    """

    model = Track

    def get_deets(self):
        return str(self.get_object())

    def do_thing(self):
        self.get_object().play()


class Hide(AdminAction, DetailView):
    model = Track

    def do_thing(self):
        self.get_object().hide()
        messages.success(self.request, u"'{}' hidden".format(self.get_object().title))


class Unhide(AdminAction, DetailView):
    model = Track

    def do_thing(self):
        self.get_object().unhide()
        messages.success(self.request, u"'{}' unhidden".format(self.get_object().title))


class LockMetadata(AdminAction, DetailView):
    model = Track

    def do_thing(self):
        self.get_object().lock_metadata()
        messages.success(
            self.request,
            "'{}' will no longer have its metadata updated in library updates".format(
                self.get_object().title
            ),
        )


class UnlockMetadata(AdminAction, DetailView):
    model = Track

    def do_thing(self):
        self.get_object().unlock_metadata()
        messages.success(
            self.request,
            "Library updates will affect '{}' again".format(self.get_object().title),
        )


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
        messages.success(self.request, 'vote added')
        return redirect(reverse('vote:index'))


class MakeBlock(TrackSpecificAdminMixin, CreateView):
    """
    Block a track.
    """

    model = Block
    fields = ['reason']
    template_name = 'block.html'

    def form_valid(self, form):
        block = form.save(commit=False)
        block.track = self.get_track()
        block.show = Show.current()

        try:
            block.save()
        except ValidationError as e:
            return self.handle_validation_error(e)

        messages.success(self.request, u"'{}' blocked".format(self.get_object().title))

        return redirect(reverse('vote:index'))


class Unblock(AdminAction, DetailView):
    model = Track

    def do_thing(self):
        block = get_object_or_404(Block, track=self.get_object(), show=Show.current())
        messages.success(
            self.request, u"'{}' unblocked".format(self.get_object().title)
        )
        block.delete()


class MakeBlockWithReason(AdminAction, DetailView):
    """
    Block a track for a particular reason.
    """

    model = Track

    def do_thing(self):
        Block(
            reason=self.request.GET.get('reason'),
            track=self.get_object(),
            show=Show.current(),
        ).save()
        messages.success(self.request, u"'{}' blocked".format(self.get_object().title))


class MakeShortlist(AdminAction, DetailView):
    """
    Add a track to the shortlist.
    """

    model = Track

    def do_thing(self):
        self.get_object().shortlist()
        messages.success(
            self.request, u"'{}' shortlisted".format(self.get_object().title)
        )


class MakeDiscard(AdminAction, DetailView):
    """
    Discard a track.
    """

    model = Track

    def do_thing(self):
        self.get_object().discard()
        messages.success(
            self.request, u"'{}' discarded".format(self.get_object().title)
        )


class OrderShortlist(AdminMixin, JSApiMixin, View):
    def do_thing(self, post):
        current = Show.current()
        indescriminate_shortlist = current.shortlist_set.all()
        shortlisted = current.shortlisted()
        pks = post.getlist('shortlist[]')

        min_placeholder_index = max([s.index for s in indescriminate_shortlist]) + 1

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
        messages.success(self.request, u"'{}' reset".format(self.get_object().title))


class LibraryUploadView(AdminMixin, FormView):
    template_name = 'upload.html'
    form_class = LibraryUploadForm

    def form_valid(self, form):
        self.request.session['library_update'] = {
            'inudesu': form.cleaned_data['inudesu'],
            'library_xml': form.cleaned_data['library_xml'].read().decode('utf-8'),
        }

        return redirect(reverse('vote:admin:confirm_upload'))


class LibraryUploadConfirmView(DestructiveAdminAction, TemplateView):
    """
    Update the library.
    """

    template_name = 'library_update.html'

    def update_library(self, dry_run: bool) -> list[dict[str, Any]]:
        library_update = self.request.session['library_update']
        return update_library(
            plistlib.loads(library_update['library_xml'].encode()),
            inudesu=library_update['inudesu'],
            dry_run=dry_run,
        )

    def get_deets(self):
        return self.update_library(dry_run=True)

    def do_thing(self):
        changes = self.update_library(dry_run=False)
        messages.success(self.request, 'library updated')
        return changes


class ToggleAbuser(AdminAction, DetailView):
    model = TwitterUser

    def get_object(self):
        return self.model.objects.get(user_id=self.kwargs['user_id'])

    def do_thing(self):
        user = self.get_object()
        user.is_abuser = not user.is_abuser
        fmt = u"{} condemned" if user.is_abuser else u"{} redeemed"
        messages.success(self.request, fmt.format(self.get_object()))
        user.save()


class HiddenTracks(AdminMixin, ListView):
    model = Track
    template_name = 'hidden.html'
    context_object_name = 'tracks'

    def get_queryset(self):
        qs = self.model.objects.filter(hidden=True, inudesu=False)
        return qs.order_by('-added')


class InuDesuTracks(AdminMixin, ListView):
    model = Track
    template_name = 'inudesu.html'
    context_object_name = 'tracks'

    def get_queryset(self):
        return self.model.objects.filter(hidden=False, inudesu=True)


class ArtlessTracks(AdminMixin, ListView):
    model = Track
    template_name = 'artless.html'
    context_object_name = 'tracks'
    paginate_by = 20

    def get_queryset(self):
        return self.model.objects.filter(background_art='')


class BadTrivia(AdminMixin, ListView):
    model = Request
    template_name = 'trivia.html'
    context_object_name = 'requests'

    def get_queryset(self):
        return self.model.objects.all().order_by('-created')


class ShortlistSelection(SelectionAdminAction):
    fmt = u'{} shortlisted'

    def do_thing(self) -> None:
        for track in self.get_queryset():
            track.shortlist()


class HideSelection(SelectionAdminAction):
    fmt = u'{} hidden'

    def do_thing(self) -> None:
        for track in self.get_queryset():
            track.hide()


class UnhideSelection(SelectionAdminAction):
    fmt = u'{} unhidden'

    def do_thing(self) -> None:
        for track in self.get_queryset():
            track.unhide()


class DiscardSelection(SelectionAdminAction):
    fmt = u'{} discarded'

    def do_thing(self) -> None:
        for track in self.get_queryset():
            track.discard()


class ResetShortlistAndDiscardSelection(SelectionAdminAction):
    fmt = u'{} reset'

    def do_thing(self) -> None:
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

        messages.success(self.request, 'note added')
        return redirect(reverse('vote:index'))


class RemoveNote(DestructiveAdminAction, DetailView):
    """
    Remove this note.
    """

    model = Note

    def get_deets(self) -> str:
        obj = self.get_object()

        return '"{content}"; {track}'.format(
            track=obj.track,
            content=obj.content,
        )

    def do_thing(self) -> None:
        self.get_object().delete()
        messages.success(self.request, 'note removed')


class RequestList(ElfMixin, ListView):
    template_name = 'requests.html'
    model = Request

    def get_queryset(self):
        return super().get_queryset().filter(successful=True, filled=None)


class FillRequest(ElfMixin, FormView):
    allowed_methods = ['post']
    form_class = Form

    def form_valid(self, form):
        request = get_object_or_404(
            Request,
            pk=self.kwargs['pk'],
            successful=True,
            filled__isnull=True,
        )

        request.filled = timezone.now()
        request.filled_by = self.request.user
        request.save()
        messages.success(self.request, u"request marked as filled")

        return redirect(reverse('vote:admin:requests'))


class ClaimRequest(ElfMixin, FormView):
    allowed_methods = ['post']
    form_class = Form

    def form_valid(self, form):
        if 'unclaim' in self.request.POST:
            request = get_object_or_404(
                Request,
                pk=self.kwargs['pk'],
                filled__isnull=True,
                claimant=self.request.user,
            )

            request.claimant = None
            request.save()
            messages.success(self.request, u"request unclaimed")

        elif 'claim' in self.request.POST:
            request = get_object_or_404(
                Request,
                pk=self.kwargs['pk'],
                successful=True,
                filled__isnull=True,
                claimant=None,
            )

            request.claimant = self.request.user
            request.save()
            messages.success(self.request, u"request claimed")

        return redirect(reverse('vote:admin:requests'))


class CheckMetadata(ElfMixin, FormView):
    form_class = CheckMetadataForm
    template_name = 'check_metadata.html'

    def form_valid(self, form: CheckMetadataForm) -> HttpResponse:
        context = self.get_context_data()
        track = Track(
            id3_title=form.cleaned_data['id3_title'],
            id3_artist=form.cleaned_data['id3_artist'],
            composer=form.cleaned_data['composer'],
            year=form.cleaned_data['year'],
        )
        context.update(
            {
                'track': track,
                'warnings': metadata_consistency_checks(
                    track,
                    Track.all_anime_titles(),
                    Track.all_artists(),
                    Track.all_composers(),
                ),
            }
        )
        return self.render_to_response(context)
