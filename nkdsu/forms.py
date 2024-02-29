from allauth.account import forms as allauth_forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError

from .apps.vote.forms import TriviaForm
from .apps.vote.models import TwitterUser


class RegistrationForm(TriviaForm, UserCreationForm):
    def clean_username(self) -> str:
        username = self.cleaned_data['username']
        if TwitterUser.objects.filter(screen_name__iexact=username).exists():
            raise ValidationError(
                "There's a Twitter user by this screen name who has requested music on"
                " nkd.su in the past. If you are this user, please send a message to"
                " @theshillito asking for help getting your account migrated."
            )

        return username


class ResetPasswordForm(TriviaForm, allauth_forms.ResetPasswordForm):
    pass
