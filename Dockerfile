# baleen image
#
# VERSION 1.0
FROM python:2.7
MAINTAINER Joel Pitt <joel@ideegeo.com>

RUN echo "deb-src http://http.debian.net/debian jessie main\n" \ 
    "deb-src http://http.debian.net/debian jessie-updates main\n" \
    "deb-src http://security.debian.org jessie/updates main\n" \
    >> /etc/apt/sources.list
RUN apt-get update && apt-get -y upgrade && echo 1
RUN apt-get install -y libexpat1-dev libidn11-dev python-pip git \
        libyaml-dev gearman gearman-job-server docker.io
RUN apt-get build-dep -y psycopg2

# Need to freakin' have some hosts, because we run git without
# a tty stdin, so can't accept the unknown host prompt
RUN mkdir -p ~/.ssh && ssh-keyscan github.com >> ~/.ssh/known_hosts

# create working dir
RUN mkdir -p /usr/local/baleen
WORKDIR /usr/local/baleen

RUN ls -la /usr/local/baleen
# install requirements
COPY requirements.txt /usr/local/baleen/
RUN pip install -r requirements.txt

# add all source
ADD . /usr/local/baleen/.

RUN mkdir -p /var/lib/baleen

# Ensure we don't have any left over pyc files when things get deleted
# and generate bytecode so container will start fast as possible
RUN find . -name '*.pyc' -delete && python -m compileall .

RUN python manage.py collectstatic --noinput
VOLUME ["/var/lib/baleen"]

EXPOSE 5000
CMD ["./docker_start.sh"]
