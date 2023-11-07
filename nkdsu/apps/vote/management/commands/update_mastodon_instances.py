import os
import subprocess

from django.core.management.base import BaseCommand
import requests

from nkdsu.apps import vote


SOURCE_INSTANCES = {
    'mastodon.social',
    'icosahedron.website',
}


def fmt(domain: str) -> str:
    """
    Break a domain into chunks, so that black is able to combine or rejoin it
    as necessary, but only if it's particularly long.
    """

    if len(domain) > 100:
        return '(\n        {}\n    )'.format(
            '\n        '.join(
                repr(('' if i == 0 else '.') + chunk)
                for i, chunk in enumerate(domain.split('.'))
            )
        )
    else:
        return repr(domain)


class Command(BaseCommand):
    def write_instances(self, instances: list[str]) -> None:
        module_path = os.path.join(
            os.path.dirname(vote.__file__), 'mastodon_instances.py'
        )

        with open(module_path, 'wt') as f:
            f.write(
                "# this file is populated by running `python manage.py"
                " update_mastodon_instances`\n# do not edit it by hand\n\n"
            )
            splitter = ',\n    '
            f.write(
                "MASTODON_INSTANCES: set[str] = {\n"
                f"    {splitter.join((fmt(i) for i in instances))},\n"
                "}"
            )

        subprocess.check_call(['black', module_path])

    def handle(self, *args, **kwargs) -> None:
        instances: set[str] = set()

        for source_instance in SOURCE_INSTANCES:
            instances.update(
                requests.get(f"https://{source_instance}/api/v1/instance/peers").json()
            )

        self.write_instances(sorted(instances))
