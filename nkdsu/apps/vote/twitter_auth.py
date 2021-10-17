from django.conf import settings
from social_core.backends.twitter import TwitterOAuth
from social_core.pipeline import DEFAULT_AUTH_PIPELINE
from social_django.strategy import DjangoStrategy


class NkdsuTwitterAuth(TwitterOAuth):
    def __init__(self, *args, **kwargs):
        if 'redirect_uri' in kwargs:
            kwargs['redirect_uri'] = settings.SITE_URL + kwargs['redirect_uri']
        super().__init__(*args, **kwargs)

    def get_user_details(self, response):
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
        return DEFAULT_AUTH_PIPELINE
