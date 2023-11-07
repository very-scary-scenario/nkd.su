import os

from django.core.management.base import BaseCommand
import requests

from nkdsu.apps import vote


SOURCE_INSTANCES = {
    'mastodon.social',
    'icosahedron.website',
}


class Command(BaseCommand):
    def write_instances(self, instances: list[str]) -> None:
        txt_path = os.path.join(
            os.path.dirname(vote.__file__), 'mastodon_instances.txt'
        )

        with open(txt_path, 'wt') as f:
            for instance in instances:
                f.write(f"{instance}\n")

    def handle(self, *args, **kwargs) -> None:
        instances: set[str] = set()

        for source_instance in SOURCE_INSTANCES:
            instances.update(
                requests.get(f"https://{source_instance}/api/v1/instance/peers").json()
            )

        self.write_instances(sorted(instances))
