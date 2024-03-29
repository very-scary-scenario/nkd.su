import subprocess

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **kwargs) -> None:
        call_command('update_mastodon_instances')
        print(
            subprocess.check_output(
                ['git', 'submodule', 'foreach', 'git', 'pull', 'origin', 'master']
            )
        )
