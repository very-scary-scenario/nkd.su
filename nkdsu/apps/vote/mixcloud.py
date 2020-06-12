import requests

from django.conf import settings
from django.core.cache import cache


TIMEOUT = 4


def _get_feed_items():
    page = requests.get(
        settings.MIXCLOUD_FEED_URL,
        params={'since': '0', 'limit': '100'},
        timeout=TIMEOUT,
    ).json()

    # we should page through for a while, but at a certain point it probably
    # isn't worth the load times
    for attempt in range(20):
        yield from page['data']

        next_page_url = page['paging'].get('next')
        if next_page_url is None:
            break

        page = requests.get(next_page_url, timeout=TIMEOUT).json()


def _get_items():
    # cache wrapper for _get_feed_items()

    ck = 'mixcloud:all-items'
    hit = cache.get(ck)

    if hit:
        return hit

    try:
        rv = list(_get_feed_items())
        cache.set(ck, rv, 60*20)
        return rv
    except requests.RequestException:
        # problem with the Mixcloud API; panic
        return None


def cloudcasts_for(date):
    items = _get_items()

    if items is None:
        return None

    hunting_for = date.strftime('%d/%m/%Y')
    cloudcasts = []

    for item in items:
        for cloudcast in item.get('cloudcasts', []):
            if hunting_for in cloudcast['name']:
                cloudcasts.append(cloudcast)

    return sorted(cloudcasts, key=lambda c: c['created_time'])
