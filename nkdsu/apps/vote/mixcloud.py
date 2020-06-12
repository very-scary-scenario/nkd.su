import requests

from django.conf import settings
from django.core.cache import cache


TIMEOUT = 4


def _get_items():
    next_page_url = settings.MIXCLOUD_FEED_URL

    # we should page through for a while, but at a certain point it probably
    # isn't worth the load times
    for page_index in range(20):
        ck = 'mixcloud:api-page:{}'.format(page_index)
        hit = cache.get(ck)

        if hit:
            page = hit
        else:
            page = requests.get(
                next_page_url,
                timeout=TIMEOUT,
            ).json()
            cache.set(ck, page, 60*20)

        yield from page['data']

        next_page_url = page['paging'].get('next')
        if next_page_url is None:
            break

        page = requests.get(next_page_url, timeout=TIMEOUT).json()


def cloudcasts_for(date):
    hunting_for = date.strftime('%d/%m/%Y')
    cloudcasts = []

    for item in _get_items():
        matched_item = False

        for cloudcast in item.get('cloudcasts', []):
            if hunting_for in cloudcast['name']:
                cloudcasts.append(cloudcast)
                matched_item = True

        if cloudcasts and not matched_item:
            # we've matched something, and the next item isn't also a
            # match, which means we don't need to worry about the next item
            # being a match either; the only cases where a show has
            # multiple cloudcasts, they'll be adjacent
            break

    return sorted(cloudcasts, key=lambda c: c['created_time'])
