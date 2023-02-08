from typing import TypedDict

from django.conf import settings
from django.contrib import messages
from django.http import HttpRequest
from social_core.backends.twitter import TwitterOAuth
from social_core.pipeline import DEFAULT_AUTH_PIPELINE
from social_django.strategy import DjangoStrategy

from .models import TwitterUser


class UserDetailsDict(TypedDict):
    username: str
    fullname: str


class NkdsuTwitterAuth(TwitterOAuth):
    def __init__(self, *args, **kwargs):
        redir = kwargs.get('redirect_uri') or '/'
        kwargs['redirect_uri'] = settings.SITE_URL + redir
        super().__init__(*args, **kwargs)

    def auth_allowed(self, response: dict, details: UserDetailsDict) -> bool:
        allowed = super().auth_allowed(response, details)

        # XXX social_core.pipeline.social_auth.auth_allowed throws an AuthError when these fail, which leads to a 500.
        # we should instead probably catch these and throw something else instead. i don't want to be getting emails,
        # and i want people to see these error messages. middleware, perhaps?

        try:
            existing_twitteruser = TwitterUser.objects.get(user_id=response['id'])
        except TwitterUser.DoesNotExist:
            existing_twitteruser = None

        request: HttpRequest = self.strategy.request

        if existing_twitteruser is None:
            messages.warning(
                request,
                'the account you logged in with has no history of requesting things on nkd.su; '
                'you should make a fresh account instead',
            )
            return False

        current_user = request.user

        if (
            # block auth attempts when trying to establish a new social-auth
            # link with an account that has a TwitterUser associated with
            # someone else already. make sure, though, that we don't just block
            # logging in as that person altogether. they might not have any
            # other auth method yet.
            (existing_twitteruser.profile is not None)
            and False
            # XXX i don't know how to query this second part yet. it might not
            # be possible at this part of the pipeline
        ):
            messages.warning(
                request,
                'this twitter user is already associated with an account other than yours',
            )
            return False

        if (
            # block auth attempts if this user is already signed in and already
            # has an associated twitter account. there's no reason to repeat
            # this process.
            (current_user.is_authenticated)
            and (current_user.profile.twitter_user is not None)
        ):
            messages.warning(
                request,
                f'you are already logged in, and your account is already associated with '
                f'{current_user.profile.twitter_user.screen_name}',
            )
            return False

        return allowed

    def get_user_details(self, response: dict) -> UserDetailsDict:
        """
        Like super().get_user_details(), but doesn't try to split names into
        first and last parts.
        """

        return {
            'username': response['screen_name'],
            'fullname': response['name'],
        }


class NkdsuStrategy(DjangoStrategy):
    """
    Django social auth respects the "PIPELINE" Django setting, which we're
    already using for django-pipeline, so we need to override that behaviour to
    ignore it.
    """

    def get_pipeline(self, backend=None):
        return (
            DEFAULT_AUTH_PIPELINE
            # + ('nkdsu.apps.vote.twitter_auth.link_twitteruser',)
            # + ('nkdsu.apps.vote.twitter_auth.steal_avatar',)
        )


def link_twitteruser():
    raise NotImplementedError()


def steal_avatar(response):
    profile_has_no_avatar = True  # XXX check this

    if (not response['default_profile_image']) and profile_has_no_avatar:
        pass
        # XXX steal response['profile_image_url_https'] and load it into our profile avatar field
