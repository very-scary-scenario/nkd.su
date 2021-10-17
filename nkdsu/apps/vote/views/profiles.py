from typing import Optional

from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import AbstractBaseUser
from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from django.views.generic import DetailView


User = get_user_model()


class ProfileView(DetailView):
    model = User
    context_object_name = 'object'

    def get_object(self, queryset: Optional[QuerySet[AbstractBaseUser]] = None) -> AbstractBaseUser:
        if queryset is None:
            queryset = self.get_queryset()

        return get_object_or_404(queryset, username=self.kwargs['username'])
