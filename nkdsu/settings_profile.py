from nkdsu.settings import *  # noqa

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.staticfiles',
    'django.contrib.admin',

    'django_nose',
    'djcelery',
    'pipeline',
    'south',
    'debug_toolbar',

    'nkdsu.apps.vote',
)

DEBUG_TOOLBAR_PANELS = (
    'debug_toolbar.panels.timer.TimerPanel',
    'debug_toolbar.panels.sql.SQLPanel',
    'debug_toolbar.panels.profiling.ProfilingPanel',
)

DEBUG = True
