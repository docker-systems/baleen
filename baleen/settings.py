# -*- coding: utf-8 -*-
# Django settings for baleen project.
import os

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = None

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'baleen.db',                      # Or path to database file if using sqlite3.
        # The following settings are not used with sqlite3:
        'USER': '',
        'PASSWORD': '',
        'HOST': '',                      # Empty for localhost through domain sockets or '127.0.0.1' for localhost through TCP.
        'PORT': '',                      # Set to empty string for default.
    }
}

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = []

TIME_ZONE = 'Pacific/Auckland'
LANGUAGE_CODE = 'en-nz'

SITE_ID = 1
# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

PROJECT_DIR = os.path.join(os.path.dirname(__file__), '..')
# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/var/www/example.com/media/"
MEDIA_ROOT = 'media'

SITE_URL = 'http://localhost:8000'

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://example.com/media/", "http://media.example.com/"
MEDIA_URL = 'media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/var/www/example.com/static/"
STATIC_ROOT = os.path.join(PROJECT_DIR, 'static')

# URL prefix for static files.
# Example: "http://example.com/static/", "http://static.example.com/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(PROJECT_DIR, 'baleen/static'),
    #MEDIA_ROOT
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = ''

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.core.context_processors.tz",
    "django.contrib.messages.context_processors.messages",

    "baleen.context_processors.static_files",
    "baleen.context_processors.site_processor",

    "django.core.context_processors.request",

    "allauth.account.context_processors.account",
    "allauth.socialaccount.context_processors.socialaccount",

)

AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'baleen.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'baleen.wsgi.application'

TEMPLATE_DIRS = (
    os.path.join(PROJECT_DIR, 'baleen/templates'),
)

PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    #'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
    #'django.contrib.auth.hashers.BCryptPasswordHasher',
    'django.contrib.auth.hashers.SHA1PasswordHasher',
    'django.contrib.auth.hashers.MD5PasswordHasher',
    'django.contrib.auth.hashers.CryptPasswordHasher',
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Uncomment the next line to enable the admin:
    'django.contrib.admin',
    'django.contrib.admindocs',

    'allauth',
    'allauth.account',
    'allauth.socialaccount',

    'south',
    'reversion',
    'crispy_forms',
    'jsonify',
    'django_nose',
    'sendfile',

    'baleen.project',
    'baleen.job',
    'baleen.action',
    'baleen.artifact',
)

TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
NOSE_ARGS = [
    '--with-xunit', '--with-doctest', #strange error not finding this
    '-I', 'local_settings.*'
    ]
NOSE_PLUGINS = [
    'baleen.nose_plugins.SilenceSouth',
]

#SENDFILE_BACKEND = 'sendfile.backends.xsendfile'
SENDFILE_BACKEND = 'sendfile.backends.simple'
ARTIFACT_DIR = os.path.join(PROJECT_DIR, 'build_artifacts')

BUILD_ROOT = '/var/lib/baleen/'

CRISPY_TEMPLATE_PACK = 'bootstrap'

GEARMAN_SERVER = 'localhost'
GEARMAN_JOB_LABEL = 'baleen_job'

GITHUB_HOOK_URL = SITE_URL + '/hub'

ACTION_MODULES = {
    'project': "baleen.action.project",
    'docker': "baleen.action.docker",
    'ssh': "baleen.action.ssh",
}

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
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

try:
    from local_settings import *
except ImportError:
    ALLOWED_HOSTS = []

# This is to save us having to manually add domain of the GITHUB_HOOK_URL to
# our ALLOWED_HOSTS settings
from urlparse import urlparse
github_url_parsed = urlparse(GITHUB_HOOK_URL)
ALLOWED_HOSTS.append( github_url_parsed.scheme + "://" + github_url_parsed.netloc )

import sys
#if manage.py test was called, use test settings
if 'test' in sys.argv or 'migrationcheck' in sys.argv:
    try:
        from test_settings import *
    except ImportError:
        raise
