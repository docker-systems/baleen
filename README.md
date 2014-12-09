# Baleen - Continuous Integration for your Docker stack

WARNING: This is a work in progress and liable to change a lot over the next
few months. Only work with this if you're interested in actively building
an opinionated docker CI tool.

We'll be trying to make it play nicely with docker orchestration tools (the
official ones as well as third party), but our main priority is creating
something that solves our use case.

## Install

```
docker build -t baleen:latest .
docker pull -t baleen:latest .

fig build
fig up -d db
fig run web python manage.py syncdb
fig run web python manage.py migrate --all
fig up
```



## Delete and use fresh db

Because it was a challenge to figure out the simplest way to do this:

```
docker stop POSTGRES_CONTAINER_ID
docker rm --volumes POSTGRES_CONTAINER_ID
```

## TODO:

* Need to support saving the result of running various hooks (commands that are
  run on: SUCCESS/FAILURE/COMPLETION of actions)

