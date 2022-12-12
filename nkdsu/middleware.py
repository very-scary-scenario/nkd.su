from typing import Callable

from django.http import Http404, HttpRequest, HttpResponse
from django.urls import reverse


class SocialAuthBetaMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        begin_url = reverse('social:begin', kwargs={'backend': 'twitter'})
        suffix = 'login/twitter/'
        assert begin_url.endswith(suffix)
        self.prefix = begin_url[: -len(suffix)]
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        return self.get_response(request)

    def process_view(self, request: HttpRequest, *a, **k) -> None:
        if (
            request.resolver_match is not None
            and 'social' in request.resolver_match.app_names
            and not request.user.is_authenticated
        ):
            raise Http404('for now, we pretend this does not exist')
