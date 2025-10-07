from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **kwargs) -> None:
        call_command('update_emoji_lists')
        call_command('update_mastodon_instances')
        call_command('update_mpaod')
