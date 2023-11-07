from typing import Optional

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import UpdateView

from . import VoterDetail
from ..forms import ClearableFileInput
from ..models import Profile, UserWebsite
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
                messages.warning(self.request, "that website isn't on your profile at the moment")
                return redirect('.')
            else:
                website.delete()
                messages.success(self.request, f"website {website.url!r} removed from your profile")
                return redirect('.')

        if request.POST.get('add-website') == 'yes' and request.POST.get('url'):
            if user.profile.has_max_websites():
                messages.warning(self.request, "don't you think you have enough websites already")
                return redirect('.')
            else:
                try:
                    website = user.profile.websites.create(url=request.POST['url'])
                except ValidationError as e:
                    messages.warning(self.request, ', '.join(e.messages))
                    return redirect('.')
                messages.success(self.request, f"website {website.url} added to your profile")
                return redirect('.')

        return redirect('.')

    def get_voter(self) -> Profile:
        user = self.get_object()
        assert isinstance(user, User)
        return user.profile


class UpdateProfileView(LoginRequiredMixin, UpdateView):
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
