from nkdsu.settings import *  # noqa

STATICFILES_STORAGE = 'pipeline.storage.PipelineFinderStorage'
STATIC_URL = '/static/'

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}
