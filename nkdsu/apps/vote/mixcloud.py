import requests

from django.conf import settings
from django.core.cache import cache


def _api_resp():
    ck = 'mixcloud:feed'
    hit = cache.get(ck)
    if hit:
        return hit

    try:
        rv = requests.get(
            settings.MIXCLOUD_FEED_URL,
            # we should probably be paginating here to ensure we get everything
            params={'since': '0', 'limit': '100'},
            timeout=5,
        ).json()
        cache.set(ck, rv, 60*5)
        return rv
    except requests.RequestException:
        # problem with the Mixcloud API; panic
        return None


def cloudcasts_for(date):
    resp = _api_resp()

    if resp is None:
        return None

    hunting_for = date.strftime('%d/%m/%Y')
    cloudcasts = []

    for datum in resp['data']:
        for cloudcast in datum.get('cloudcasts', []):
            if hunting_for in cloudcast['name']:
                cloudcasts.append(cloudcast)

    return sorted(cloudcasts, key=lambda c: c['created_time'])
