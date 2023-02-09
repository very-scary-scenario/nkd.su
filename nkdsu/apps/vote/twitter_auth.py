import re
from typing import TypedDict

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.http import HttpRequest
import requests
from social_core.backends.twitter import TwitterOAuth
from social_core.pipeline import DEFAULT_AUTH_PIPELINE
from social_django.models import UserSocialAuth
from social_django.strategy import DjangoStrategy

from .models import TwitterUser, avatar_upload_path


class DoNotAuthThroughTwitterPlease(BaseException):
    msg: str

    def __init__(self, msg: str) -> None:
        self.msg = msg


class UserDetailsDict(TypedDict):
    username: str
    fullname: str
    default_profile_image: bool
    profile_image_url_https: str


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
                'the twitter account you logged in with has no history of requesting things on nkd.su; '
                'you should make a account with a username and password instead'
            )

        if (
            # block auth attempts if this user is already signed in and already
            # has an associated twitter account. there's no reason to repeat
            # this process.
            (request.user.is_authenticated)
            and (request.user.profile.twitter_user is not None)
        ):
            raise DoNotAuthThroughTwitterPlease(
                'you are already logged in, and your account is already associated with '
                f'{request.user.profile.twitter_user.screen_name}. '
                'you should not associate it again',
            )

        if hasattr(existing_twitteruser, 'profile'):
            if (
                # this account is currently associated with a different user
                (existing_usa is not None)
                and (existing_twitteruser.profile.user != existing_usa.user)
            ):
                raise DoNotAuthThroughTwitterPlease(
                    'this twitter account is currently associated with an nkd.su account other than yours'
                )

            if existing_usa is None:
                raise DoNotAuthThroughTwitterPlease(
                    'this twitter account has already been adopted'
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
            'default_profile_image': response['default_profile_image'],
            'profile_image_url_https': response['profile_image_url_https'],
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
            + ('nkdsu.apps.vote.twitter_auth.link_twitteruser',)
            + ('nkdsu.apps.vote.twitter_auth.adopt_twitter_metadata',)
        )


def link_twitteruser(uid: int, user: User, *args, **kwargs) -> None:
    # this has been previously guaranteed to exist in our auth_allowed implementation
    twitter_user = TwitterUser.objects.get(user_id=str(uid))

    # and also, we should check this just to be sure:
    if hasattr(twitter_user, 'profile') and (twitter_user.profile.user != user):
        raise AssertionError(
            f'auth_allowed() messed up, because {user!r} should not have been able to log in as {twitter_user!r}; '
            f'that user was already adopted by {twitter_user.profile.user!r}'
        )

    if user.profile.twitter_user is None:
        profile = user.profile
        profile.twitter_user = twitter_user
        profile.save()


def adopt_twitter_metadata(
    request: HttpRequest, user: User, details: UserDetailsDict, *args, **kwargs
) -> None:
    profile = user.profile

    if (not details['default_profile_image']) and (not profile.avatar):
        try:
            url = details['profile_image_url_https']
            avatar = ContentFile(
                requests.get(re.sub(r'_normal(?=\.[^.]+$)', '', url)).content
            )
            profile.avatar.save(name=avatar_upload_path(profile, ''), content=avatar)
        except requests.RequestException as e:
            messages.error(
                request, f'sorry, we were unable to retrieve your twitter avatar: {e!r}'
            )

    if not profile.display_name:
        profile.display_name = details['fullname']

    profile.save()
