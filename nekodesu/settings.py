import djcelery

# note the sensitive settings blanked and commented out below; these must be
# replicated in settings_local.py in any functional nkd.su instance. Settings
# defined there will override settings here.

# unblanked but commented-out settings below are not sensitive but are
# different in production and dev environments (and also required in
# settings_local.py)

# Note that this settings file assumes that nkd.su will continue to be a
# single-site website; the email acounts and stuff would need to be changed
# were someone to set up some kind of fork.

djcelery.setup_loader()

CELERY_TIMEZONE = 'Europe/London'

BROKER_URL = "amqp://guest:guest@127.0.0.1:5672//"

EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_HOST_USER = 'nivi@musicfortheblind.co.uk'
# EMAIL_HOST_PASSWORD = ''
EMAIL_USE_TLS = True

HASHTAG = '#NekoDesu'
INUDESU_HASHTAG = '#InuDesu'
TMP_XML_PATH = '/tmp/songlibrary.xml'
REQUEST_CURATOR = 'peter.shillito@thisisthecat.com'
# AKISMET_API_KEY = ''
AKISMET_BLOG_URL = 'http://nkd.su'

TWITTER_SHORT_URL_LENGTH = 22

OPTIONS = {'timeout': 20}

# CONSUMER_KEY = ''
# CONSUMER_SECRET = ''

#@nkdsu                                                                
# READING_ACCESS_TOKEN = ''
# READING_ACCESS_TOKEN_SECRET = ''
READING_USERNAME = "nkdsu"

#@nekodesuradio
# POSTING_ACCESS_TOKEN = ''
# POSTING_ACCESS_TOKEN_SECRET = ''

import os.path
SITE_ROOT = os.path.dirname(os.path.realpath(__file__))+'/../'

DEBUG = False
TEMPLATE_DEBUG = DEBUG

ADMINS = ('Iain Dawson', 'i@bldm.us'),

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': '/home/nivi/code/nkdsu/nekodesu/db',
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
USE_L10N = True
USE_TZ = True

# MEDIA_ROOT = '/home/nivi/www/nkdsm/user/'
# MEDIA_URL = 'http://m.nkd.su/user/'
# STATIC_ROOT = '/home/nivi/www/nkdsm/'
# STATIC_URL = 'http://m.nkd.su/'

STATICFILES_DIRS = ()

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

# SECRET_KEY = ''

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'nekodesu.urls'

WSGI_APPLICATION = 'nekodesu.wsgi.application'

# TEMPLATE_DIRS = ('/home/nivi/code/nkdsu/html/')

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'vote',
    'djcelery',
    'south',
)

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

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.debug',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'django.contrib.auth.context_processors.auth',
    'django.contrib.messages.context_processors.messages',
    'vote.context_processors.nkdsu_context_processor',
)

LOGIN_URL = '/login'
LOGOUT_URL = '/logout'
LOGIN_REDIRECT_URL = '/'
# TWITTER_ARCHIVE = '/home/nivi/code/hrldcpr/twitter-archive/tweets/'

from nekodesu.settings_local import *
