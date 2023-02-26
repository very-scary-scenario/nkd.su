import os

from dateutil.relativedelta import SA, relativedelta

import django_stubs_ext

django_stubs_ext.monkeypatch()

# note the sensitive settings marked as 'secret' below; these must be
# replicated in settings_local.py in any functional nkd.su instance. Settings
# defined there will override settings here.

# unblanked but commented-out settings below are not sensitive but are
# different in production and dev environments (and also required in
# settings_local.py)

# Note that this settings file assumes that nkd.su will continue to be a
# single-site website; the email acounts and stuff would need to be changed
# were someone to set up some kind of fork.

PROJECT_DIR = os.path.realpath(os.path.join(__file__, '..'))
PROJECT_ROOT = os.path.realpath(os.path.join(PROJECT_DIR, '..'))

CELERY_TIMEZONE = 'Europe/London'

BROKER_URL = "amqp://guest:guest@127.0.0.1:5672//"

# EMAIL_HOST = ''
# EMAIL_PORT = 587
# EMAIL_HOST_USER = ''
# EMAIL_HOST_PASSWORD = ''
EMAIL_USE_TLS = True

# stuff about when the show is
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
REQUEST_CURATOR = 'peter@nekodesu.radio'

TWEET_LENGTH = 280

#: The maximum number of tracks that can be associated with a single Vote object
MAX_REQUEST_TRACKS = 6

OPTIONS = {'timeout': 20}

# social-auth
SOCIAL_AUTH_TWITTER_KEY = ''  # secret
SOCIAL_AUTH_TWITTER_SECRET = ''  # secret
SOCIAL_AUTH_JSONFIELD_ENABLED = True
SOCIAL_AUTH_STRATEGY = 'nkdsu.apps.vote.twitter_auth.NkdsuStrategy'

MIXCLOUD_USERNAME = 'NekoDesu'

LASTFM_API_KEY = ''  # secret
LASTFM_API_SECRET = ''  # secret

DEBUG = False
TEMPLATE_DEBUG = DEBUG

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(PROJECT_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'social_django.context_processors.backends',
                'social_django.context_processors.login_redirect',
                'nkdsu.apps.vote.context_processors.nkdsu_context_processor',
            ],
        },
    },
]

ADMINS = (('colons', 'nkdsu@colons.co'),)

MANAGERS = ADMINS

ATOMIC_REQUESTS = True
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

STATICFILES_DIRS = (os.path.join(PROJECT_DIR, 'static'),)

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'pipeline.finders.PipelineFinder',
)

SECRET_KEY = 'please replace me with something decent in production'  # secret

MIDDLEWARE = [
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'nkdsu.middleware.SocialAuthHandlingMiddleware',
]

ROOT_URLCONF = 'nkdsu.urls'

WSGI_APPLICATION = 'nkdsu.wsgi.application'

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.messages',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.postgres',
    'django_extensions',
    'pipeline',
    'social_django',
    'nkdsu.apps.vote',
]

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {'require_debug_false': {'()': 'django.utils.log.RequireDebugFalse'}},
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    },
}

AUTHENTICATION_BACKENDS = [
    'nkdsu.apps.vote.twitter_auth.NkdsuTwitterAuth',
    'django.contrib.auth.backends.ModelBackend',
]

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 10,
        },
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LOGIN_URL = 'login'
LOGOUT_URL = 'logout'
LOGIN_REDIRECT_URL = 'vote:index'

# STATIC

STATICFILES_STORAGE = 'pipeline.storage.PipelineManifestStorage'

PIPELINE = {
    'CSS_COMPRESSOR': 'pipeline.compressors.yuglify.YuglifyCompressor',
    'YUGLIFY_BINARY': '/usr/bin/env npx yuglify',
    'JS_COMPRESSOR': 'pipeline.compressors.uglifyjs.UglifyJSCompressor',
    'UGLIFYJS_BINARY': '/usr/bin/env npx uglifyjs',
    'UGLIFYJS_ARGUMENTS': '--mangle',
    'COMPILERS': ['pipeline.compilers.sass.SASSCompiler'],
    'SASS_BINARY': '/usr/bin/env npx sass',
    'DISABLE_WRAPPER': True,
    'STYLESHEETS': {
        'main': {
            'source_filenames': [
                'scss/main.scss',
            ],
            'output_filename': 'css/main.min.css',
        }
    },
    'JAVASCRIPT': {
        'base': {
            'source_filenames': [
                'js/libs/details-polyfill.js',
                'js/libs/Sortable.js',
                'js/csrf.js',
                'js/collapse-toggle.js',
                'js/select.js',
                'js/messages.js',
                'js/ajax-actions.js',
                'js/roulette.js',
                'js/shortlist-sorting.js',
                'js/menu.js',
                'js/dark.js',
                'js/browse.js',
                'js/toggle-group-folds.js',
            ],
            'output_filename': 'js/min/base.js',
        },
        'check-metadata': {
            'source_filenames': [
                'js/libs/jsmediatags.min.js',
                'js/check-metadata.js',
            ],
            'output_filename': 'js/min/check-metadata.js',
        },
    },
}

try:
    from nkdsu.settings_local import *  # noqa
except ImportError:
    pass
