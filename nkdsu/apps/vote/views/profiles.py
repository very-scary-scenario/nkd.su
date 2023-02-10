from typing import Optional

from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import UpdateView

from . import VoterDetail
from ..forms import ClearableFileInput
from ..models import Profile
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

    def get_voter(self) -> Profile:
        user = self.get_object()
        assert isinstance(user, User)
        return user.profile


class UpdateProfileView(LoginRequiredMixin, UpdateView):
    model = Profile
    fields = ['display_name', 'avatar']
    template_name = 'edit_profile.html'

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
