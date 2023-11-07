import os


def _get_mastodon_instances() -> set[str]:
    with open(
        os.path.join(os.path.dirname(__file__), 'mastodon_instances.txt'), 'rt'
    ) as f:
        return set((i.strip() for i in f.readlines() if i.strip()))


MASTODON_INSTANCES: set[str] = _get_mastodon_instances()
