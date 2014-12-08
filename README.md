# Baleen - Continuous Integration for your Docker stack

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

