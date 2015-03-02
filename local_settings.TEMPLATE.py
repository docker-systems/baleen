import os

e = os.environ

DATABASES = {
    'default': {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "HOST": e.get('BALEEN_DB_HOST', 'db_1'),
        "PORT": e.get('BALEEN_DB_PORT', 5432),
        "NAME": e.get('BALEEN_DB_NAME', 'postgres'),
        "USER": e.get('POSTGRES_USER', 'postgres'),
        "PASSWORD": e.get('POSTGRES_PASSWORD', ''),
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
GITHUB_HOOK_URL = SITE_URL
BALEEN_EMAIL = "Baleen <baleen@example.com>"

HIPCHAT_TOKEN = None
HIPCHAT_ROOM = 'development'
MAILGUN_KEY = ''
MAILGUN_URL = ''

DOCKER_HOST = ''

DOCKER_REGISTRIES = {
    'DOCKER REGISTRY HOST': {
        'user': '',
        'password': '',
        'email': '',
    }
}

# Example logging to console if the default isn't showing you enough info.
#LOGGING = {
    #'version': 1,
    ## set to True will disable all logging except that specified, unless
    ## nothing is specified except that django.db.backends will still log,
    ## even when set to True, so disable explicitly
    #'disable_existing_loggers': True,
    #'handlers': {
        #'null': {
            #'level': 'DEBUG',
            #'class': 'django.utils.log.NullHandler',
            #},
        #'console': {
            #'level': 'DEBUG',
            #'class': 'logging.StreamHandler',
            #},
        #},
    #'loggers': {
        ## Comment or Uncomment these to turn on/off logging output
        #'django.db.backends': {
            #'handlers': ['null'],
            #'propagate': False,
            #},
    #}
#}

