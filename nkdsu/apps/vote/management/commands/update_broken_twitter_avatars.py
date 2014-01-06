import logging

import requests
from tweepy import TweepError

from django.core.management.base import BaseCommand

from nkdsu.apps.vote.models import TwitterUser


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        'For every TwitterUser in the database, check to see if the avatar '
        'works. If it does not, update it'
    )

    def handle(self, *args, **options):
        for user in TwitterUser.objects.all():
            resp = requests.get(user.user_image)
            if resp.status_code != 200:
                try:
                    user.update_from_api()
                except TweepError:
                    pass  # this user probably does not exist
                else:
                    print 'updated {0}'.format(user)
