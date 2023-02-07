from typing import Any
from urllib.parse import parse_qs, urlparse

from django.contrib.auth import views as auth_views
from django.shortcuts import get_object_or_404

from .apps.vote.forms import RegistrationForm
from .apps.vote.models import Track
from .apps.vote.utils import vote_tweet_intent_url
from .mixins import MarkdownView


class LoginView(MarkdownView, auth_views.LoginView):
    template_name = auth_views.LoginView.template_name
    title = 'login'
    filename = 'TWITTER.md'

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)

        twitter_vote_url = None
        tracks = []

        query_string = urlparse(context[self.redirect_field_name]).query
        query = parse_qs(query_string)

        if query is not None:
            tracks = [
                get_object_or_404(Track, pk=pk)
                for pk_string in query.get('t', [])
                for pk in pk_string.split(',')
            ]

        if tracks:
            twitter_vote_url = vote_tweet_intent_url(tracks)

        return {
            **context,
            'is_vote': bool(tracks),  # this is naive, but we don't use ?t= for a lot
            'twitter_vote_url': twitter_vote_url,
            'registration_form': RegistrationForm(),
        }
