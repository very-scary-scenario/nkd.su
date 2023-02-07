from typing import Callable

from django.http import HttpRequest, HttpResponse
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
