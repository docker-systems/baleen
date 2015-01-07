#!/bin/sh
echo "Running syncdb and any pending migrations..."
./manage.py syncdb --noinput --migrate

: ${SHELL:='0'}

echo "Starting supervisord..."
echo "Starting Baleen..."
if [ "$SHELL" = '1' ]; then
    supervisord -c supervisord.conf
    /bin/bash
else
    supervisord --nodaemon -c supervisord.conf
fi

