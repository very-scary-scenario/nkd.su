from cache_utils.decorators import cached
import requests

from django.conf import settings


@cached(60*10)
def _api_resp():
    return requests.get(settings.MIXCLOUD_FEED_URL,
                        params={'since': '0'}).json()


def cloudcasts_for(date):
    resp = _api_resp()
    hunting_for = date.strftime('%d/%m/%Y')
    cloudcasts = []

    for datum in resp['data']:
        for cloudcast in datum['cloudcasts']:
            if hunting_for in cloudcast['name']:
                cloudcasts.append(cloudcast)

    return sorted(cloudcasts, key=lambda c: c['created_time'])
