import os

from .settings import INSTALLED_APPS, MIDDLEWARE, PROJECT_DIR  # noqa

TEMPLATE_DEBUG = DEBUG = True

CACHES = {
    'default': {
        # i think this is a reasonable default:
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',

        # when you want to test something like stats generation, the cache will
        # just get in your way. disable it by using the dummy cache:
        # 'BACKEND': 'django.core.cache.backends.dummy.DummyCache',

        # if you want to use the database cache, be sure to run `python
        # manage.py createcachetable` after you've uncommented these:
        # 'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        # 'LOCATION': 'nk_cache_table',
    }
}

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(PROJECT_DIR, 'db'),
    }
}

# to enable the debug toolbar, uncomment these:
# INTERNAL_IPS = ('127.0.0.1',)
# INSTALLED_APPS = INSTALLED_APPS + ['debug_toolbar']
# MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
