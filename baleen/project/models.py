from django.db import models
from django.conf import settings
from django.core.urlresolvers import reverse

import logging
import subprocess
import tempfile
import json
import os
import stat
import re
import gearman

from contextlib import closing
from base64 import urlsafe_b64encode
from hashlib import sha256

from baleen.job.models import Job
from baleen.utils import statsd_label_converter, generate_ssh_key, mkdir_p, cd

log = logging.getLogger('baleen.project')

class Project(models.Model):
    name = models.CharField(max_length=255, unique=True,
            help_text='Project title')
    site_url = models.URLField(max_length=255, null=True, blank=True,
            verbose_name="Site URL",
            help_text='A URL to where this project deploys to')

    scm_url = models.CharField(max_length=255, null=True, blank=True,
            verbose_name="SCM Repostory URL",
            help_text='URL to git repo')
    #scm_sync_success = models.BooleanField(default=False, editable=False,
            #help_text='Was the last attempt to sync with the SCM successful?')

    github_token = models.CharField(max_length=255, editable=False,
            help_text="The token for the URL that GitHub's post-receive hook will use")
    github_data_received = models.BooleanField(default=False, editable=False,
            help_text='Have we received data from GitHub for this project?')
    branch = models.CharField(max_length=255, null=True, blank=True,
            help_text="Deploy only on commits to this git branch")

    manual_config = models.BooleanField(default=False,
            help_text="If this is true we will ignore any Baleen config file in the repo")

    # Use this key pair for getting source from github
    # public_key should be pasted into the projects deploy keys
    public_key = models.TextField(editable=False)
    private_key = models.TextField(editable=False)

    def __init__(self, *args, **kwargs):
        super(Project, self).__init__(*args, **kwargs)
        self._original_scm_url = self.scm_url

    def __unicode__(self):
        return "Project %s" % self.name

    def save(self):
        do_clone = False
        if self.pk is None:
            self.github_token = self.generate_github_token()
            self.private_key, self.public_key = generate_ssh_key()
        if self._original_scm_url != self.scm_url:
            # The revision control url changed, we need to fire a task to
            # checkout the code and configure based on the baleen.yml
            # (unless manual_config=True)
            do_clone = True
        super(Project, self).save()
        if do_clone:
            gearman_client = gearman.GearmanClient([settings.GEARMAN_SERVER])
            gearman_client.submit_job(settings.GEARMAN_JOB_LABEL, json.dumps(
                {
                    'project': self.id,
                    'generate_actions': True
                }), background=True)

    @property
    def project_dir(self):
        return re.sub(r'[^a-zA-Z0-9]',' ', self.name)

    def sync_repo(self):
        # ensure BUILD_ROOT exists
        mkdir_p(settings.BUILD_ROOT)

        # This is a little complicated because we want to set up git to use
        # the ssh key for this project. We do this by using the GIT_SSH environment
        # variable, and dumping our private key to a temporary file (that only
        # the current user can read/write)
        fd, identity_fn = tempfile.mkstemp()
        with closing(os.fdopen(fd, 'w')) as tf:
            tf.write(self.private_key)

        fd, git_ssh_fn = tempfile.mkstemp()
        template = """#!/bin/bash\nssh -i %s $@\n"""
        temp_git_wrap = template % identity_fn
        with closing(os.fdopen(fd, 'w')) as tf:
            tf.write(temp_git_wrap)

        # temp file isn't executable by default
        st = os.stat(git_ssh_fn)
        os.chmod(git_ssh_fn, st.st_mode | stat.S_IEXEC)

        os.environ['GIT_SSH'] = git_ssh_fn
        
        with cd(settings.BUILD_ROOT):
            git_checkout = subprocess.Popen(
                ["git", "clone", self.scm_url, self.project_dir],
                stdout=subprocess.PIPE
                ).stdout.read()
        del os.environ['GIT_SSH']

        # Clean up after outselves
        os.remove(identity_fn)
        os.remove(git_ssh_fn)

        result = git_checkout.decode('utf-8')
        log.debug('Git checkout stdout: %s' % result)

    def _raw_yaml(self):
        """ Read yaml file defining build """
        with cd(settings.BUILD_ROOT):
            pass

    @property
    def statsd_name(self):
        return statsd_label_converter(self.name)

    @classmethod
    def generate_github_token(self):
        seed = os.urandom(32)
        token = sha256(sha256(seed).digest()).digest()
        github_token = urlsafe_b64encode(token)[:-2]
        return github_token

    def github_push_url(self):
        return reverse('github_url', kwargs={'github_token': self.github_token} )

    @property
    def ordered_actions(self):
        return self.action_set.all().order_by('index')

    def current_job(self):
        qs = Job.objects.filter(project=self, finished_at=None, started_at__isnull=False)
        return qs.first()

    def last_job(self):
        """ Get the last deployment job.

        If prefer_active is True, then ignore rejected jobs and get the most
        recent active job provided it isn't too far back in our history.
        """
        running = self.current_job()
        if not running:
            return Job.objects.filter(project=self).order_by('-received_at').first()
        else:
            return running

    def last_successful_job(self):
        qs = Job.objects.filter(project=self, success=True).order_by('-finished_at')
        return qs.first()

    def clear_unfinished_jobs(self):
        """ Mark all jobs, with no finished time, as complete but unsuccessful """
        unfinished = Job.objects.filter(project=self, finished_at=None, started_at__isnull=False)
        for j in unfinished:
            j.record_done(success=False)
        print "Marked %d jobs as done." % len(unfinished)

    def collect_all_authorized_keys(self, include_comments=True):
        all_hosts = {}
        for action in self.ordered_actions:
            user_and_host = (action.username, action.host)
            all_hosts.setdefault(user_and_host,[])
            all_hosts[user_and_host].append(action.authorized_keys_entry)
        for user_and_host in all_hosts:
            if include_comments:
                keys = ['## ' + self.name]
                keys.extend(all_hosts[user_and_host])
            all_hosts[user_and_host] = '\n'.join(keys)
        return all_hosts
