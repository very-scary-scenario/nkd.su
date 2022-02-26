from nkdsu.settings import *  # noqa

HASHTAG = '#usedoken'

STATIC_URL = '/static/'

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}
