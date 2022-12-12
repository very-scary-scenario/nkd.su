from typing import Optional

from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import AbstractBaseUser
from django.db.models import QuerySet
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.views.generic import DetailView, UpdateView

from ..models import Profile
from ..utils import get_profile_for


User = get_user_model()


class ProfileView(DetailView):
    model = User
    context_object_name = 'object'

    def get_object(
        self, queryset: Optional[QuerySet[AbstractBaseUser]] = None
    ) -> AbstractBaseUser:
        if queryset is None:
            queryset = self.get_queryset()

        return get_object_or_404(queryset, username=self.kwargs['username'])


class UpdateProfileView(UpdateView):
    model = Profile
    fields = ['display_name', 'avatar']
    template_name = 'edit_profile.html'

    def get_object(self, queryset: Optional[QuerySet[Profile]] = None) -> Profile:
        if not self.request.user.is_authenticated:
            raise Http404()  # XXX this view should be properly gated to only authed users
        return get_profile_for(self.request.user)
