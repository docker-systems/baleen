# Be careful with this file, as it is used as a template for the debian
# package setup. Feel free to copy it to local_settings.py and change/fill in
# as you like though.
import os

e = os.environ

DATABASES = {
    'default': {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": e.get('BALEEN_DB_NAME', 'baleen'),
        "USER": e.get('BALEEN_DB_USER', 'baleen'),
        "PORT": e.get('BALEEN_DB_PORT', 5432),
        "HOST": e.get('BALEEN_DB_HOST', ''),
        "PASSWORD": e.get('BALEEN_DB_PASSWORD', ''),
    }
}

# Change this to True if you are doing local development
DEBUG = False

# Uncomment this while doing local dev
# SENDFILE_BACKEND = 'sendfile.backends.development'

SITE_URL = ''
MEDIA_ROOT = '/var/lib/baleen/uploaded'

SERVER_EMAIL = ''
DEFAULT_FROM_EMAIL = SERVER_EMAIL

GEARMAN_SERVER = ''

EMAIL_HOST = ''
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
EMAIL_PORT = ''
EMAIL_USE_TLS = ''

ALLOWED_HOSTS = ''

MAILGUN_KEY = ''
