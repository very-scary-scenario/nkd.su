from typing import TypedDict

from django.conf import settings
from django.contrib import messages
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

        if existing_twitteruser is None:
            messages.warning(
                self.strategy.request,
                'the account you logged in with has no history of requesting things on nkd.su; '
                'you should make a fresh account instead',
            )
            return False

        current_user = self.strategy.request.user

        if (current_user is not None) and (
            current_user.profile.twitter_user is not None
        ):
            messages.warning(
                self.strategy.request,
                f'you are already logged in, and your account is already associated with '
                f'{current_user.profile.twitter_user.screen_name}',
            )
            # this user is already associated with a TwitterUser instance.
            # going through this is only necessary when logged out or adopting a twitter account.
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
