from typing import Any, Callable, Sequence

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from social_core.exceptions import NotAllowedToDisconnect

from .apps.vote.twitter_auth import DoNotAuthThroughTwitterPlease


class SocialAuthHandlingMiddleware:
    """
    Middleware for doing nkd.su-specific workarounds for unwanted Python Social
    Auth behaviour.
    """

    prefix: str
    get_response: Callable[[HttpRequest], HttpResponse]

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        # establish what the base social_auth URL is, so that we can only
        # affect social-auth URLs
        begin_url = reverse('social:begin', kwargs={'backend': 'twitter'})
        suffix = 'login/twitter/'
        assert begin_url.endswith(suffix)  # make sure
        self.prefix = begin_url[: -len(suffix)]

        assert (
            self.prefix == '/s/'
        ), self.prefix  # make sure both the derived and expected values are the same

        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        return self.get_response(request)

    def process_view(
        self,
        request: HttpRequest,
        view_func: Callable,
        view_args: Sequence[Any],
        view_kwargs: dict[str, Any],
    ) -> HttpResponse:
        if not request.path.startswith(self.prefix):
            # this is not a social auth request. do nothing
            return view_func(request, *view_args, **view_kwargs)

        # since we're catching exceptions, we might want to manually roll-back database transactions here
        try:
            return view_func(request, *view_args, **view_kwargs)
        except DoNotAuthThroughTwitterPlease as e:
            messages.warning(request, e.msg)
        except NotAllowedToDisconnect:
            messages.warning(
                request,
                'you have to set a password or you will not be able to log back in',
            )

        if request.user.is_authenticated:
            return redirect(
                reverse(
                    'vote:profiles:profile',
                    kwargs={'username': request.user.username},
                )
            )
        else:
            return redirect(reverse('login'))
