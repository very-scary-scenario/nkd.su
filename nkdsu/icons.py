import os
import re
from typing import Iterable

from django.conf import settings


def _get_icons() -> Iterable[tuple[str, str]]:
    with open(
        os.path.join(
            settings.PROJECT_ROOT,
            'node_modules',
            '@fortawesome',
            'fontawesome-free',
            'less',
            '_variables.less',
        ),
        'rt',
    ) as varfile:
        for line in varfile.readlines():
            if match := re.match(r'^@fa-var-([a-z0-9-]+): "\\([0-9a-f]+)";', line):
                yield (match.groups()[0], chr(int(match.groups()[1], base=16)))


ICONS: dict[str, str] = {slug: char for slug, char in _get_icons()}

assert ('trash-can', '\uf2ed') in ICONS.items()
