from django.conf import settings
from social_core.backends.twitter import TwitterOAuth


class NkdsuTwitterAuth(TwitterOAuth):
    def __init__(self, *args, **kwargs):
        kwargs['redirect_uri'] = settings.SITE_URL + kwargs['redirect_uri']
        super().__init__(*args, **kwargs)

    def get_user_details(self, response):
        """
        Like super().get_user_details(), but doesn't try to split names into
        first and last parts.
        """

        return {
            'username': response['screen_name'],
            'email': response.get('email', ''),
            'fullname': response['name'],
        }
