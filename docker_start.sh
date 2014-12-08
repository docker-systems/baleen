#!/bin/sh
echo "Starting supervisord..."
supervisord -c supervisord.conf
echo "Starting Baleen..."

python manage.py runserver 0.0.0.0:8000
