import os

e = os.environ

DATABASES = {
    'default': {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": e.get('BALEEN_DB_NAME', 'postgres'),
        "USER": e.get('BALEEN_DB_USER', 'postgres'),
        "PORT": e.get('BALEEN_DB_PORT', 5432),
        "HOST": e.get('BALEEN_DB_HOST', 'db_1'),
        #"PASSWORD": e.get('BALEEN_DB_PASSWORD', ''),
    }
}

# Change this to True if you are doing local development
DEBUG = False

# Uncomment this while doing local dev
# SENDFILE_BACKEND = 'sendfile.backends.development'

#SERVER_EMAIL = ''
#DEFAULT_FROM_EMAIL = SERVER_EMAIL

#EMAIL_HOST = ''
#EMAIL_HOST_USER = ''
#EMAIL_HOST_PASSWORD = ''
#EMAIL_PORT = ''
#EMAIL_USE_TLS = ''

#ALLOWED_HOSTS = ''

ADMINS = ( ('admin','admin@example.com'), )
SITE_URL = ''
SECRET_KEY = ''
GITHUB_HOOK_URL = SITE_URL + '/hub'
BALEEN_EMAIL = "Baleen <baleen@example.com>"

MAILGUN_KEY = '',
MAILGUN_URL = '',

DOCKER_HOST = ''

DOCKER_REGISTRIES = {
    'DOCKER REGISTRY HOST': {
        'user': '',
        'password': '',
        'email': '',
    }
}
