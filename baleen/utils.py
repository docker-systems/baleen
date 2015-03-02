import re
import os
import tarfile
import errno
import paramiko
import json

from urllib2 import Request, urlopen
from hashlib import sha256
from base64 import urlsafe_b64encode
from contextlib import contextmanager
from StringIO import StringIO

from django.db import models
from django.conf import settings


def statsd_label_converter(name):
    # Remove all non-word characters (everything except numbers and letters)
    s = re.sub(r"[^\w\s]", '', name)

    # Replace all runs of whitespace with a single underscore
    s = re.sub(r"\s+", '_', s)
    return s.lower()


class FirstQuerySet(models.query.QuerySet):
    def first(self):
        try:
            return self[0]
        except IndexError:
            return None


class ManagerWithFirstQuery(models.Manager):
    def get_query_set(self):
        return FirstQuerySet(self.model)


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


@contextmanager
def cd(newdir):
    prevdir = os.getcwd()
    os.chdir(newdir)
    try:
        yield
    finally:
        os.chdir(prevdir)


def make_tarfile(output_filename, source_dir):
    with tarfile.open(output_filename, "w:gz") as tar:
        tar.add(source_dir, arcname=os.path.basename(source_dir))


def generate_ssh_key(length=2048):
    key = paramiko.RSAKey.generate(length)
    buf = StringIO()
    key.write_private_key(buf)
    private_key = buf.getvalue()
    public_key = 'ssh-rsa %s' % key.get_base64()
    return private_key, public_key


def generate_github_token():
    seed = os.urandom(32)
    token = sha256(sha256(seed).digest()).digest()
    github_token = urlsafe_b64encode(token)[:-2]
    return github_token


def get_credential_key_pair(name, project=None, user=None):
    from baleen.project.models import Credential

    args = {}
    if project:
        args['project'] = project
    elif user:
        args['user'] = user
    else:
        raise Exception('Project or User needs to be specified when creating key pair')

    pub_args = dict(args)
    pub_args['name'] = name + '_public'
    priv_args = dict(args)
    priv_args['name'] = name + '_private'
    try:
        public = Credential.objects.get(**pub_args)
        priv = Credential.objects.get(**priv_args)
    except Credential.DoesNotExist:
        priv_args['value'], pub_args['value'] = generate_ssh_key()

        priv = Credential(**priv_args)
        priv.save()

        public = Credential(**pub_args)
        public.save()
    return priv, public


def full_path_split(path):
    folders=[]
    while 1:
        path,folder=os.path.split(path)

        if folder!="":
            folders.append(folder)
        else:
            if path!="":
                folders.append(path)

            break

    folders.reverse()
    return folders


def team_notify(msg, color='yellow', room=None):
    if getattr(settings, "HIPCHAT_TOKEN") is None:
        return

    if room is None:
        room = settings.HIPCHAT_ROOM

    # API V2, send message to room:
    url = 'https://api.hipchat.com/v2/room/%s/notification' % room
    headers = {
        "content-type": "application/json",
        "authorization": "Bearer %s" % settings.HIPCHAT_TOKEN}
    datastr = json.dumps({
        'message': msg,
        'color': color,
        'message_format': 'text',
        'notify': False
        })
    request = Request(url, headers=headers, data=datastr)
    uo = urlopen(request)
    #rawresponse = ''.join(uo)
    uo.close()
    assert uo.code == 204
