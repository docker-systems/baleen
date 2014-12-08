#!./_env/bin/python
# -*- coding: utf-8 -*-
"""
WSGI config for baleen project.

This module contains the WSGI application used by Django's development server
and any production WSGI deployments. It should expose a module-level variable
named ``application``. Django's ``runserver`` and ``runfcgi`` commands discover
this application via the ``WSGI_APPLICATION`` setting.
"""
import os
import sys
sys.path.append('/var/www/django/baleen2')

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "baleen.settings")

# A relative path to file which, if exists, forces the handler to respond with server
# maintenance message.
MAINTENANCE_LOCK_FILE = 'maintenance.lock'

# Relative path to HTML file sent as a maintenance message.
# This file should be encoded in UTF-8.
MAINTENANCE_MESSAGE_FILE = 'maintenance.html'

# The message sent in case MAINTENANCE_MESSAGE_FILE doesn't exist or is not readable.
# This should be an unicode plain text string.
MAINTENANCE_MESSAGE_FALLBACK = u"Server is down for maintenance. Please try again later."

################################################################################

BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__),'..'))

def maintenance_wsgi_application(environ, start_response):
    """
WSGI handler (see PEP333) responding with server maintenance message from a HTML file.
If a message file doesn't exist, responds with default, plain text message.
Uses UTF-8 encoding for all its input and output.
"""
    status = '503 Service Unavailable'
    headers = []
    body = []
    try:
        # Try to open a HTML file with maintenance message
        file = open(os.path.join(BASE_PATH, MAINTENANCE_MESSAGE_FILE), 'r')
        body.append(file.read())
        file.close()
        headers.append(('Content-Type', 'text/html; charset=UTF-8'))
    except IOError:
        # Apparently message HTML file doesn't exist. Fallback to plain text message.
        body.append(MAINTENANCE_MESSAGE_FALLBACK.encode('utf-8') + "\r\n")
        headers.append(('Content-Type', 'text/plain; charset=UTF-8'))
    start_response(status, headers)
    return body

if not os.path.exists(os.path.join(BASE_PATH, MAINTENANCE_LOCK_FILE)):
    # Maintenance lock file doesn't exist - running Django app

    # This application object is used by any WSGI server configured to use this
    # file. This includes Django's development server, if the WSGI_APPLICATION
    # setting points here.
    from django.core.wsgi import get_wsgi_application
    application = get_wsgi_application()
else:
    # Maintenance lock file exists - respond with maintenance message
    application = maintenance_wsgi_application
