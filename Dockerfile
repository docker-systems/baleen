# baleen image
#
# VERSION 1.0
FROM python:2.7
MAINTAINER Joel Pitt <joel@ideegeo.com>

RUN echo "deb-src http://http.debian.net/debian jessie main\n" \ 
    "deb-src http://http.debian.net/debian jessie-updates main\n" \
    "deb-src http://security.debian.org jessie/updates main\n" \
    >> /etc/apt/sources.list
RUN apt-get update && apt-get -y upgrade
RUN apt-get install -y libexpat1-dev libidn11-dev python-pip git \
        libyaml-dev gearman gearman-job-server docker.io
RUN apt-get build-dep -y psycopg2

RUN useradd -ms /bin/bash baleen

# create app dir and data dir
RUN mkdir -p /usr/local/baleen && mkdir -p /var/lib/baleen

WORKDIR /usr/local/baleen
# install requirements
COPY requirements.txt /usr/local/baleen/
RUN pip install -r requirements.txt

# Need to freakin' have some hosts, because we run git without
# a tty stdin, so can't accept the unknown host prompt
#
# NOTE: this needs to be the same user as the baleen workers run as,
# which is currently "root" as they need access to the docker daemon to
# build containers.
#
# If we can eventually control the uid of the container, and assign it
# to a "docker" group with access to the docker socket, then that user
# will need this known_hosts file too.
RUN mkdir -p ~/.ssh && ssh-keyscan github.com >> ~/.ssh/known_hosts && cat ~/.ssh/known_hosts 

# add all source
ADD . /usr/local/baleen/.

# Ensure we don't have any left over pyc files when things get deleted
# and generate bytecode so container will start fast as possible
RUN find . -name '*.pyc' -delete && python -m compileall .

RUN python manage.py collectstatic --noinput
ENV PYTHONPATH /config
RUN chown -R baleen:baleen /usr/local/baleen /var/lib/baleen
VOLUME ["/var/lib/baleen"]

CMD ["./docker_start.sh"]
