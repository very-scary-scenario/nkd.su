from typing import Any, Optional

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User as DjangoUser
from django.core.exceptions import ValidationError
from django.db.models import Q, QuerySet
from django.forms import BooleanField, IntegerField, ModelForm, TextInput
from django.http import HttpRequest, HttpResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, UpdateView
from django.views.generic.base import ContextMixin
import ujson

from . import VoterDetail
from ..emoji import EMOJI
from ..forms import ClearableFileInput
from ..mixins import BreadcrumbMixin
from ..models import Profile, UserTrackList, UserWebsite
from ..utils import get_profile_for


User = get_user_model()


class ProfileView(VoterDetail):
    model = User
    context_object_name = 'object'

    def get_object(
        self, queryset: Optional[QuerySet[AbstractBaseUser]] = None
    ) -> AbstractBaseUser:
        if queryset is None:
            queryset = self.get_queryset()

        return get_object_or_404(queryset, username=self.kwargs['username'])

    def post(self, request: HttpRequest, username: str) -> HttpResponse:
        user = self.get_object()
        assert isinstance(user, User)

        if request.user != user:
            messages.warning(self.request, "this isn't you. stop that.")
            return redirect('.')

        delete_pk = request.POST.get('delete-website')
        if delete_pk is not None:
            try:
                website = user.profile.websites.get(pk=delete_pk)
            except UserWebsite.DoesNotExist:
                messages.warning(
                    self.request, "that website isn't on your profile at the moment"
                )
                return redirect('.')
            else:
                website.delete()
                messages.success(
                    self.request, f"website {website.url!r} removed from your profile"
                )
                return redirect('.')

        if request.POST.get('add-website') == 'yes' and request.POST.get('url'):
            if user.profile.has_max_websites():
                messages.warning(
                    self.request, "don't you think you have enough websites already"
                )
                return redirect('.')
            else:
                try:
                    website = user.profile.websites.create(url=request.POST['url'])
                except ValidationError as e:
                    messages.warning(self.request, ', '.join(e.messages))
                    return redirect('.')
                messages.success(
                    self.request, f"website {website.url!r} added to your profile"
                )
                return redirect('.')

        return redirect('.')

    def get_voter(self) -> Profile:
        user = self.get_object()
        assert isinstance(user, User)
        return get_profile_for(user)

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        profile = self.get_voter()

        track_lists = UserTrackList.objects.filter(user=profile.user)

        if self.request.user != profile.user:
            track_lists = track_lists.filter(public=True)

        return {
            **super().get_context_data(),
            'track_lists': track_lists,
        }


class UpdateProfileView(LoginRequiredMixin, UpdateView[Profile, ModelForm]):
    model = Profile
    fields = ['display_name', 'avatar']
    template_name = 'edit_profile.html'
    base_breadcrumbs = [(reverse_lazy("vote:profiles:edit-profile"), "edit profile")]

    def get_form(self):
        form = super().get_form()
        form.fields['avatar'].widget = ClearableFileInput()
        return form

    def get_success_url(self) -> str:
        return reverse(
            'vote:profiles:profile', kwargs={'username': self.request.user.username}
        )

    def get_object(self, queryset: Optional[QuerySet[Profile]] = None) -> Profile:
        if not self.request.user.is_authenticated:
            raise RuntimeError('LoginRequiredMixin should have prevented this')
        return get_profile_for(self.request.user)


class UserTrackListMixin(ContextMixin):
    model: type[UserTrackList]
    request: HttpRequest
    kwargs: dict[str, Any]

    def get_curator(self) -> DjangoUser:
        return get_object_or_404(User, username=self.kwargs['user'])

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        return {
            **super().get_context_data(**kwargs),
            'curator': self.get_curator(),
        }

    def get_queryset(self) -> QuerySet[UserTrackList]:
        q = Q(public=True)
        if self.request.user.is_authenticated:
            q = q | Q(user=self.request.user)
        return self.model.objects.filter(q)


class UserTrackListListView(
    BreadcrumbMixin, UserTrackListMixin, ListView[UserTrackList]
):
    model = UserTrackList
    template_name = 'user_track_list_list.html'

    def get_breadcrumbs(self) -> list[tuple[Optional[str], str]]:
        user = self.get_curator()
        return [(user.profile.get_absolute_url(), user.profile.display_name)]

    def get_queryset(self) -> QuerySet[UserTrackList]:
        return super().get_queryset().filter(user__username=self.kwargs['user'])


class ModifyUserTrackList(UserTrackListMixin, UpdateView[UserTrackList, ModelForm]):
    model = UserTrackList

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if self.request.user.is_anonymous or self.request.user != self.get_curator():
            return HttpResponseNotAllowed("you cannot modify another user's track list")

        if 'delete' in request.POST:
            track_list = self.get_object()
            name = track_list.name
            track_list.delete()
            messages.success(self.request, f"track list {name!r} deleted")
            return redirect(self.request.user.profile.get_absolute_url())

        return super().post(request, *args, **kwargs)

    def form_valid(self, form: ModelForm) -> HttpResponse:
        try:
            return super().form_valid(form)
        except ValidationError as e:
            form.instance.refresh_from_db()
            form.add_error(None, e)
            return self.form_invalid(form)

    def get_object(
        self, queryset: Optional[QuerySet[UserTrackList]] = None
    ) -> UserTrackList:
        return get_object_or_404(
            queryset if queryset is not None else self.get_queryset(),
            user__username=self.kwargs['user'],
            slug=self.kwargs['slug'],
        )


class UserTrackListView(BreadcrumbMixin, ModifyUserTrackList):
    model = UserTrackList
    template_name = 'user_track_list_detail.html'
    fields = ['name', 'public', 'icon', 'description']

    def get_breadcrumbs(self) -> list[tuple[Optional[str], str]]:
        curator = self.get_curator()
        return [
            (curator.profile.get_absolute_url(), curator.profile.display_name),
        ]

    def get_form_class(self) -> type[ModelForm]:
        fc = super().get_form_class()
        fc.base_fields['icon'].widget = TextInput()
        fc.base_fields['icon'].help_text = (
            'please provide one (1) emoji to use as an icon for this track list'
        )
        return fc

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        return {**super().get_context_data(**kwargs), 'emoji_json': ujson.dumps(EMOJI)}


class UserTrackListModifyMembersView(ModifyUserTrackList):
    fields = []

    def get_form_class(self) -> type[ModelForm]:
        form = super().get_form_class()
        playlist = list(self.get_object().playlist())

        return type(
            'MembersForm',
            (form,),
            {
                **{f'index_{t.pk}': IntegerField() for t in playlist},
                **{f'remove_{t.pk}': BooleanField(required=False) for t in playlist},
            },
        )

    def form_valid(self, form: ModelForm) -> HttpResponse:
        new_playlist = sorted(
            (
                t
                for t in self.get_object().tracks.all()
                if not form.cleaned_data[f'remove_{t.pk}']
            ),
            key=lambda t: form.cleaned_data[f'index_{t.pk}'],
        )
        raise RuntimeError(new_playlist)

    def form_invalid(self, form: ModelForm) -> HttpResponse:
        messages.warning(
            self.request,
            (
                str(form.errors)
                if settings.DEBUG
                else 'reordering invalid; perhaps the tracks in this list changed while you had the page loaded?'
            ),
        )
        return redirect(form.instance.get_absolute_url())
