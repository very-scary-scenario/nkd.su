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
                " nkd.su in the past. If you are this user, you'll need to log in with"
                " Twitter to claim that username. Otherwise, choose another name. "
            )

        return username
