from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin
from django.forms import Form
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic import FormView, ListView, View

from ..anime import get_anime
from ..elfs import is_elf
from ..forms import CheckMetadataForm
from ..models import ElfShelving, Request, Track
from ..update_library import metadata_consistency_checks


class ElfMixin(LoginRequiredMixin):
    """
    A mixin for views that only elfs (or staff) can see.
    """

    @classmethod
    def as_view(cls, **kw):
        return user_passes_test(is_elf)(super().as_view(**kw))


class RequestList(ElfMixin, ListView):
    template_name = 'requests.html'
    model = Request

    def get_queryset(self):
        return super().get_queryset().filter(filled=None)


class FillRequest(ElfMixin, FormView):
    allowed_methods = ['post']
    form_class = Form

    def form_valid(self, form: Form) -> HttpResponse:
        assert self.request.user.is_authenticated  # enforced by ElfMixin

        request = get_object_or_404(
            Request,
            pk=self.kwargs['pk'],
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

    def form_valid(self, form: Form) -> HttpResponse:
        assert self.request.user.is_authenticated  # enforced by ElfMixin

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
                filled__isnull=True,
                claimant=None,
            )

            request.claimant = self.request.user
            request.save()
            messages.success(self.request, u"request claimed")

        return redirect(reverse('vote:admin:requests'))


class ShelfRequest(ElfMixin, FormView):
    allowed_methods = ['post']
    form_class = Form

    def form_valid(self, form: Form) -> HttpResponse:
        assert self.request.user.is_authenticated  # enforced by ElfMixin

        request = get_object_or_404(Request, pk=self.kwargs['pk'])
        reason = self.request.POST.get('reason')

        if not reason:
            messages.error(self.request, 'please explain your shelf actions')

        elif 'shelf' in self.request.POST:
            if request.is_shelved:
                messages.warning(self.request, 'request was already shelved')
            else:
                ElfShelving.objects.create(
                    request=request, reason_created=reason, created_by=self.request.user
                )
                messages.success(self.request, 'request shelved')

        elif 'unshelf' in self.request.POST:
            if not request.is_shelved:
                messages.warning(self.request, 'request is not shelved')
            else:
                shelving = get_object_or_404(
                    request.shelvings.filter(disabled_at__isnull=True)
                )
                shelving.disabled_at = timezone.now()
                shelving.disabled_by = self.request.user
                shelving.reason_disabled = reason
                shelving.save()
                messages.success(self.request, 'request unshelved')

        else:
            raise Http404('no action specified')

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
        context.update({
            'track': track,
            'warnings': metadata_consistency_checks(
                track,
                Track.all_anime_titles(),
                Track.all_artists(),
                Track.all_composers(),
            ),
        })
        return self.render_to_response(context)


class UnmatchedAnimeTitles(ElfMixin, View):
    def get(self, request: HttpRequest) -> HttpResponse:
        return HttpResponse(
            content='\n'.join(
                sorted(t for t in Track.all_anime_titles() if not get_anime(t))
            ),
            content_type='text/plain',
        )
