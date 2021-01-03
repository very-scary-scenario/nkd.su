import logging
from time import sleep

from django.core.management.base import BaseCommand
from tweepy import TweepError

from nkdsu.apps.vote.models import TwitterUser


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        'For every TwitterUser in the database, check to see if the avatar '
        'works. If it does not, update it'
    )

    def handle(self, *args, **options):
        for user in TwitterUser.objects.all():
            try:
                user.update_from_api()
                user.get_avatar(size=None, from_cache=False)
                user.get_avatar(size='original', from_cache=False)
            except TweepError:
                # this user probably does not exist, but we might be getting
                # rate limited
                pass

            sleep(5)
