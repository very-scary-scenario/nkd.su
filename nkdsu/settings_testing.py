from nkdsu.settings import *  # noqa

DEBUG = False

HASHTAG = '#usedoken'

STATIC_URL = '/static/'

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}
