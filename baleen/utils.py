import re
import os
import tarfile
import errno
import paramiko

from contextlib import contextmanager
from StringIO import StringIO

from django.db import models


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
