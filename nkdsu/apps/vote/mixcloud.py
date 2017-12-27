import requests

from django.conf import settings


# @cached(60*10)
def _api_resp():
    try:
        return requests.get(
            settings.MIXCLOUD_FEED_URL,
            params={'since': '0'},
            timeout=3,
        ).json()
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
