# Baleen - Continuous Integration for your Docker stack

"Filtering out the bad builds since 2014"

http://en.wikipedia.org/wiki/Baleen

WARNING: This is a work in progress and liable to change a lot over the next
few months. Only work with this if you're interested in actively building
an opinionated docker CI tool.

We'll be trying to make it play nicely with docker orchestration tools (the
official ones as well as third party), but our main priority is creating
something that solves our use case.

![Project page](https://github.com/docker-systems/baleen/raw/master/docs/project_page.png)

## What it will do

It takes a git repository location and clones the repo. A `baleen.yml` file
describes the container dependencies, what containers to build (a repo can
define more than one container), and how to test the built containers.
On success, the containers are tagged and pushed to a docker registry. Then the
orchestration service is notified that new containers exist and they should be
pulled and restarted.

The two features we really needed which no one else provides (at the time we
started this project) are:

- *container dependencies for testing* - if you need certain containers to
  exist, in order to do testing of the container behaviour, then you can. While
  ideally you'd have unit tests without dependencies able to run during the
  build process, not all systems are amiable to this approach. Additionally,
  inter-container tests allow for system-level integration testing.
- *automatic fetching of dependencies* - if you have 10 repositories which each
  define a container that provides a microservice, then you can just include
  a repositories that depends on the rest of them and Baleen will import the rest
  and automatically create projects for each of them (assuming the repositories
  each have a `baleen.yml` file.)

In addition, it will allow dependencies to specifiy the git commit of
a dependency that needs to be present and successfully built before the
dependent container can build/test/deploy.

This is liable to evolve.

## What it currently does

- Fetch a repo.
- Build a container.
- Test a container.
- Extract test artifacts from test container (currently only supports Python's xunit.xml and
  coverage.xml, htmlcov outputs).
- Tag build container with `latest`

## Install

Suggested method of start up, for local development at least, is to 
define `POSTGRES_USER` and `POSTGRES_PASSWORD` environment variables to pass
through to fig (alternatively you can edit fig.yml to set them).

You also need to setup a baleen config container. This allows you to provide
your custom `local_settings.py` to the baleen container. To do so:

```
cp local_settings.TEMPLATE.py local_settings.py
# Make any changes to local_settings.py you like
cat local_settings.py | \
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

## Testing your baleen.yml

It can be annoying to have to iterative update your `baleen.yml` to ensure it's
working. Each time you want to make a change, you have to push and wait for the
baleen web UI to show progress (not always returning detailed errors, since
there are sometimes edge conditions we haven't handled).

To test your repo with a `baleen.yml`, first edit `fig.yml` so that the repo is
accessable to the container. e.g. 

```yaml
web:
  # ...
  volumes:
   - /path/to/your/repo:/usr/local/repo
```

Then 

```sh
# Ensure the DB is running
POSTGRES_USER=baleen POSTGRES_PASSWORD=baleen fig up -d db
# Get a shell
POSTGRES_USER=baleen POSTGRES_PASSWORD=baleen fig run web /bin/bash
# Inside the container:
./manage.py worker --build /usr/local/repo
```

This will run the build process in the foreground. Notes:

- At the moment it still needs to make temporary records in the database, but
  eventually the plan is to separate the execution model from the persistence
  layer.
- The output depends on your `LOGGING` setting. There is an example in
  `local_settings.TEMPLATE.py` to dump all DEBUG statements to console
  if the output doesn't have enough info to debug why something failed.

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

## Supporters

This project is a collaboration between [Dragonfly
Science](https://dragonfly.co.nz) and [iwantmyname](https://iwantmyname.com) to
solve some of their challenges with reliably building and testing containers.
