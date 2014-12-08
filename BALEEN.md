# Baleen

"Filtering out the bad builds since 2014"

http://en.wikipedia.org/wiki/Baleen

This document is to describe the changes planned to convert deployhub to
a effective docker build tool.

## Overview

To implement:

- Allow build process to be specified in config/yaml file in repo (setting up
  a project should be as simple as pointing it at a repo and/or adding a github
  hook)
- builds within docker containers as the default build environment
- separate BUILD/TEST/DEPLOY steps, with a plugin system (plugins can provide
  a way of building, testing, or deploying). Projects define the type of each
  step, or can skip it.
- One TEST plugin needs to support having other containers/projects built first
  and then spinning them up to run current containers tests. See Build Config
  below.

To remove:

- Remove dragonfab and fabric specific commands
- Remove per command ssh keys for controllng remote execution


## Test Config

We need a way to define how to run an integration test between containers.
The container being tested should be launched with a particular ENV variable,
say `TEST=1`, but also tends to need a database or other containers to
communicate with.

There are several formats out there already for defining relationships between
containers. It would be good to reuse one of these if possible:

- fig
- http://decking.io/

## coreos integration

IWMN want to use coreos as our platform for running containers. Smoothly
integrating our baleen with coreos should will make deployment after a successful
build easier.
