import requests
from tweepy import TweepError

from django.core.management.base import BaseCommand

from nkdsu.apps.vote.models import TwitterUser


class Command(BaseCommand):
    help = (
        'For every TwitterUser in the database, check to see if the avatar '
        'works. If it does not, update it'
    )

    def handle(self, *args, **options):
        for user in TwitterUser.objects.all():
            resp = requests.get(user.user_image)
            if resp.status_code != 200:
                print (
                    '\ngot HTTP {code} resolving image for {user} at {url}, '
                    'updating...'.format(
                        code=resp.status_code,
                        user=user.screen_name,
                        url=user.user_image,
                    )
                )
                try:
                    user.update_from_api()
                except TweepError:
                    print (
                        'error correcting user {user}; probably a deleted '
                        'account'.format(user=user.screen_name)
                    )
                else:
                    print 'updated image successfully'
