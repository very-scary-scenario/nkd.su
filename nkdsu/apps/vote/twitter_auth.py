from typing import TypedDict

from django.conf import settings
from django.http import HttpRequest
from social_core.backends.twitter import TwitterOAuth
from social_core.pipeline import DEFAULT_AUTH_PIPELINE
from social_django.models import UserSocialAuth
from social_django.strategy import DjangoStrategy

from .models import TwitterUser


class DoNotAuthThroughTwitterPlease(BaseException):
    msg: str

    def __init__(self, msg: str) -> None:
        self.msg = msg


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

        try:
            existing_twitteruser = TwitterUser.objects.get(user_id=int(response['id']))
        except TwitterUser.DoesNotExist:
            existing_twitteruser = None

        try:
            existing_usa = UserSocialAuth.objects.get(uid=str(response['id']))
        except UserSocialAuth.DoesNotExist:
            existing_usa = None

        request: HttpRequest = self.strategy.request

        if existing_twitteruser is None:
            raise DoNotAuthThroughTwitterPlease(
                'the account you logged in with has no history of requesting things on nkd.su; '
                'you should make a fresh account instead',
            )

        if (
            # block auth attempts when trying to establish a new social-auth
            # link with an account that has a TwitterUser associated with
            # someone else already. make sure, though, that we don't just block
            # logging in as that person altogether. they might not have any
            # other auth method yet.
            (hasattr(existing_twitteruser, 'profile'))
            and (
                (
                    # this account is currently associated with a different user
                    (existing_usa is not None)
                    and (existing_twitteruser.profile.user != existing_usa.user)
                )
                or (
                    # this twitter account has been adopted and disconnected. this
                    # is the ideal end state for this nkd.su account, let's not do
                    # anything else
                    (existing_usa is None)
                )
            )
        ):
            raise DoNotAuthThroughTwitterPlease(
                'this twitter user is already associated with an account other than yours',
            )

        if (
            # block auth attempts if this user is already signed in and already
            # has an associated twitter account. there's no reason to repeat
            # this process.
            (request.user.is_authenticated)
            and (request.user.profile.twitter_user is not None)
        ):
            raise DoNotAuthThroughTwitterPlease(
                f'you are already logged in, and your account is already associated with '
                f'{request.user.profile.twitter_user.screen_name}',
            )

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
            # XXX both of these need to be uncommented:
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
