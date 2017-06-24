import os

import djcelery

# note the sensitive settings marked as 'secret' below; these must be
# replicated in settings_local.py in any functional nkd.su instance. Settings
# defined there will override settings here.

# unblanked but commented-out settings below are not sensitive but are
# different in production and dev environments (and also required in
# settings_local.py)

# Note that this settings file assumes that nkd.su will continue to be a
# single-site website; the email acounts and stuff would need to be changed
# were someone to set up some kind of fork.

djcelery.setup_loader()

PROJECT_DIR = os.path.realpath(os.path.join(__file__, '..'))
PROJECT_ROOT = os.path.realpath(os.path.join(PROJECT_DIR, '..'))

CELERY_TIMEZONE = 'Europe/London'

BROKER_URL = "amqp://guest:guest@127.0.0.1:5672//"

EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_HOST_USER = 'nivi@musicfortheblind.co.uk'
# EMAIL_HOST_PASSWORD = ''
EMAIL_USE_TLS = True

# stuff about when the show is
from dateutil.relativedelta import SA, relativedelta
SHOWTIME = relativedelta(
    weekday=SA,
    hour=21,
    minute=0,
    second=0,
    microsecond=0,
)
SHOW_END = relativedelta(
    weekday=SA,
    hour=23,
    minute=0,
    second=0,
    microsecond=0,
)

HASHTAG = '#NekoDesu'
INUDESU_HASHTAG = '#InuDesu'
TMP_XML_PATH = '/tmp/songlibrary.xml'
REQUEST_CURATOR = 'peter.shillito@thisisthecat.com'

TWITTER_SHORT_URL_LENGTH = 22

OPTIONS = {'timeout': 20}

CONSUMER_KEY = ''  # secret
CONSUMER_SECRET = ''  # secret

#@nkdsu
READING_ACCESS_TOKEN = ''  # secret
READING_ACCESS_TOKEN_SECRET = ''  # secret
READING_USERNAME = "nkdsu"

#@nekodesuradio
POSTING_ACCESS_TOKEN = ''  # secret
POSTING_ACCESS_TOKEN_SECRET = ''  # secret

MIXCLOUD_FEED_URL = 'http://api.mixcloud.com/NekoDesu/feed/'

LASTFM_API_KEY = ''  # secret
LASTFM_API_SECRET = ''  # secret

DEBUG = False
TEMPLATE_DEBUG = DEBUG

ADMINS = ('colons', 'nkdsu@colons.co'),

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(PROJECT_DIR, 'db'),
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
    }
}

TIME_ZONE = 'Europe/London'
LANGUAGE_CODE = 'en-gb'
SITE_ID = 1
USE_I18N = False
USE_L10N = False
USE_TZ = True

# these URLs will not work when DEBUG is False; set up your webserver to serve
# static files from appropriate places and make liberal use of collectstatic
SITE_URL = 'https://nkd.su'
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(PROJECT_DIR, 'staticfiles')
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(PROJECT_DIR, 'media')

STATICFILES_DIRS = (
    os.path.join(PROJECT_DIR, 'static'),
)

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

SECRET_KEY = 'please replace me with something decent in production'  # secret

TEMPLATE_LOADERS = (
    ('django.template.loaders.cached.Loader', (
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    )),
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'nkdsu.urls'

WSGI_APPLICATION = 'nkdsu.wsgi.application'

TEMPLATE_DIRS = os.path.join(PROJECT_DIR, 'templates')

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.messages',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    'django.contrib.admin',

    'django_nose',
    'django_orphaned',
    'djcelery',
    'pipeline',
    'south',
    'debug_toolbar',

    'nkdsu.apps.vote',
)

SOUTH_MIGRATION_MODULES = {
    'djcelery': 'djcelery.south_migrations',
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

LOGIN_URL = 'login'
LOGOUT_URL = 'logout'
LOGIN_REDIRECT_URL = 'vote:index'

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.debug',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'django.core.context_processors.request',
    'django.contrib.auth.context_processors.auth',
    'django.contrib.messages.context_processors.messages',
    'nkdsu.apps.vote.context_processors.nkdsu_context_processor',
)

## STATIC

STATICFILES_STORAGE = 'pipeline.storage.PipelineCachedStorage'

PIPELINE_COMPILERS = ('pipeline.compilers.less.LessCompiler',)

PIPELINE_CSS_COMPRESSOR = None
PIPELINE_JS_COMPRESSOR = 'pipeline.compressors.slimit.SlimItCompressor'

PIPELINE_DISABLE_WRAPPER = True

PIPELINE_CSS = {
    'main': {
        'source_filenames': [
            'less/main.less',
        ],
        'output_filename': 'css/main.min.css',
    }
}

PIPELINE_JS = {
    'base': {
        'source_filenames': [
            'js/libs/jquery.js',
            'js/libs/jquery.cookie.js',
            'js/libs/jquery.pjax.js',
            'js/csrf.js',
            'js/collapse-toggle.js',
            'js/bindpjax.js',
            'js/select.js',
            'js/messages.js',
            'js/ajax-actions.js',
        ],
        'output_filename': 'js/min/base.js',
    },
    'ui': {
        'source_filenames': [
            'js/libs/jquery-ui.js',
            'js/libs/jquery.ui.sortable.js',
        ],
        'output_filename': 'js/min/ui.js',
    },
}

TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

ORPHANED_APPS_MEDIABASE_DIRS = {
    'vote': {
        'root': MEDIA_ROOT,
    }
}

try:
    from nkdsu.settings_local import *  # noqa
except ImportError:
    from sys import argv
    if 'test' not in argv:
        raise
