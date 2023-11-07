import os
import subprocess

from django.core.management.base import BaseCommand
import requests

from nkdsu.apps import vote


SOURCE_INSTANCES = {
    'mastodon.social',
    'icosahedron.website',
}


class Command(BaseCommand):
    def write_instances(self, instances: list[str]) -> None:
        module_path = os.path.join(
            os.path.dirname(vote.__file__), 'mastodon_instances.py'
        )

        with open(module_path, 'wt') as f:
            f.write(
                "# this file is populated by running `python manage.py update_mastodon_instances`\n\n"
            )
            f.write(f"MASTODON_INSTANCES = {{ {', '.join((repr(i) for i in instances))} }}")

        subprocess.check_call(['black', module_path])

    def handle(self, *args, **kwargs) -> None:
        instances: set[str] = set()

        for source_instance in SOURCE_INSTANCES:
            instances.update(
                requests.get(f"https://{source_instance}/api/v1/instance/peers").json()
            )

        self.write_instances(sorted(instances))
