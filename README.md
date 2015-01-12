# Baleen - Continuous Integration for your Docker stack

"Filtering out the bad builds since 2014"

http://en.wikipedia.org/wiki/Baleen

WARNING: This is a work in progress and liable to change a lot over the next
few months. Only work with this if you're interested in actively building
an opinionated docker CI tool.

We'll be trying to make it play nicely with docker orchestration tools (the
official ones as well as third party), but our main priority is creating
something that solves our use case.

## Install

Suggested method of start up, for local development at least, is to 
define `POSTGRES_USER` and `POSTGRES_PASSWORD` environment variables to pass
through to fig (alternatively you can edit fig.yml to set them).

You also need to setup a baleen config container. This allows you to provide
your custom `local_settings.py` to the baleen container. To do so:

```
cp local_settings.TEMPLATE.py local_settings.py`
# Make any changes to local_settings.py you like
cat ../local_settings.py | \
        docker run --volume /config -i --name baleen-config ubuntu \
        /bin/bash -c 'cat > /config/local_settings.py'
```

The fig config is setup to use the `--volumes-from` directive against the
baleen-config container.

Then run:

```sh
# Build container
fig build
# Note: you may need to start up the db by itself first since it can take
a moment to initialise
POSTGRES_USER=baleen POSTGRES_PASSWORD=baleen fig up -d db
# Start the web service, it will sync db models and perform migrations if
# needed
POSTGRES_USER=baleen POSTGRES_PASSWORD=baleen fig up
# You'll need a super user
fig run web python manage.py createsuperuser
```

## Delete and use fresh db

If you get the db in a broken state and want to start from scratch:

```sh
POSTGRES_CONTAINER_ID=baleen_db_1
docker stop $POSTGRES_CONTAINER_ID
docker rm --volumes $POSTGRES_CONTAINER_ID
```

`POSTGRES_CONTAINER_ID` will probably be `baleen_db_1` if you're using fig.

## coreos integration

IWMN want to use coreos as our platform for running containers. Smoothly
integrating our baleen with coreos should will make deployment after a successful
build easier.
