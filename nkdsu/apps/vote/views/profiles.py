from typing import Any, Optional

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User as DjangoUser
from django.core.exceptions import ValidationError
from django.db.models import Q, QuerySet
from django.forms import ModelForm
from django.http import HttpRequest, HttpResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, UpdateView
from django.views.generic.base import ContextMixin

from . import VoterDetail
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

    def get_user(self) -> DjangoUser:
        return get_object_or_404(User, username=self.kwargs['user'])

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        return {
            **super().get_context_data(**kwargs),
            'user': self.get_user(),
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
        user = self.get_user()
        return [(user.profile.get_absolute_url(), user.profile.display_name)]

    def get_queryset(self) -> QuerySet[UserTrackList]:
        return super().get_queryset().filter(user__username=self.kwargs['user'])


class UserTrackListView(
    BreadcrumbMixin, UserTrackListMixin, UpdateView[UserTrackList, ModelForm]
):
    model = UserTrackList
    template_name = 'user_track_list_detail.html'
    fields = ['name', 'public', 'icon', 'description']

    def get_breadcrumbs(self) -> list[tuple[Optional[str], str]]:
        user = self.get_user()
        return [
            (user.profile.get_absolute_url(), user.profile.display_name),
            (
                reverse('vote:profiles:track-lists', kwargs={'user': user.username}),
                'track lists',
            ),
        ]

    def form_valid(self, form: ModelForm) -> HttpResponse:
        if self.request.user != self.get_user():
            return HttpResponseNotAllowed("you cannot modify another user's track list")
        return super().form_valid(form)

    def get_object(
        self, queryset: Optional[QuerySet[UserTrackList]] = None
    ) -> UserTrackList:
        return get_object_or_404(
            queryset if queryset is not None else self.get_queryset(),
            user__username=self.kwargs['user'],
            name=self.kwargs['name'],
        )
