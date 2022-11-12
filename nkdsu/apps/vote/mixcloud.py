import logging
from json import JSONDecodeError
from typing import Any

from django.conf import settings
from django.core.cache import cache
import requests


logger = logging.getLogger(__name__)

TIMEOUT = 4

MIXCLOUD_FEED_URL = 'https://api.mixcloud.com/{}/cloudcasts/'
MIXCLOUD_PAGE_LIMIT = 100


def _get_cloudcasts():
    # we should page through for a while, but at a certain point it probably
    # isn't worth the load times
    for page_index in range(20):
        url = MIXCLOUD_FEED_URL.format(settings.MIXCLOUD_USERNAME)
        ck = 'mixcloud:api-page:{}'.format(page_index)

        hit = cache.get(ck)

        if hit:
            page = hit
        else:
            try:
                resp = requests.get(url, params={
                    'limit': MIXCLOUD_PAGE_LIMIT,
                    'offset': page_index * MIXCLOUD_PAGE_LIMIT,
                }, timeout=TIMEOUT)
            except requests.RequestException as e:
                # mission failed; we'll get 'em next time
                logger.exception(e)
                break

            try:
                page = resp.json()
            except JSONDecodeError:
                logger.exception(resp.text)
                return []

            cache.set(ck, page, 60*20)

        data = page.get('data', [])

        if not data:
            break

        yield from data


def cloudcasts_for(date) -> list[Any]:
    hunting_for = date.strftime('%d/%m/%Y')
    cloudcasts = []

    for cloudcast in _get_cloudcasts():
        matched_item = False

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
