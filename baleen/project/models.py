from django.db import models
from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils.text import slugify

import logging
import json
import re
import gearman

from baleen.job.models import Job
from baleen.artifact.models import output_types, ActionOutput

from baleen.utils import (
        statsd_label_converter,
        cd,
        generate_github_token,
        get_credential_key_pair
        )

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
    creator = models.ForeignKey('auth.User', null=True)

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
    public_key = models.ForeignKey('Credential', null=True, blank=True,
            related_name='public_key_for', on_delete=models.SET_NULL)
    private_key = models.ForeignKey('Credential', null=True, blank=True,
            related_name='private_key_for', on_delete=models.SET_NULL)

    def __init__(self, *args, **kwargs):
        super(Project, self).__init__(*args, **kwargs)
        self._original_scm_url = self.scm_url

    def __unicode__(self):
        return "Project %s" % self.name

    def action_plan(self):
        from baleen.action import parse_build_definition

        #bd = self.builddefinition_set.all().order_by('created_at').first()
        bd = self.builddefinition_set.all().order_by('commit').first()
        return parse_build_definition(self, bd)

    def save(self):
        do_clone = False
        if not self.github_token:
            self.github_token = generate_github_token()
        if None in (self.public_key, self.private_key):
            cred_name = 'deploykey_' + self.name
            self.private_key, self.public_key = get_credential_key_pair(cred_name, self)

        if self._original_scm_url != self.scm_url:
            # The revision control url changed, we need to fire a task to
            # checkout the code and configure based on the baleen.yml
            # (unless manual_config=True)
            do_clone = True

        super(Project, self).save()
        if do_clone:
            from baleen.job.models import manual_run
            manual_run(self)
            #gearman_client = gearman.GearmanClient([settings.GEARMAN_SERVER])
            #gearman_client.submit_job(settings.GEARMAN_JOB_LABEL, json.dumps(
                #{
                    #'group': 'project',
                    #'action': 'clone_repo',
                    #'name': 'Clone repo for project %s' % self.name,
                    #'index': 0,
                    #'project': self.id,
                    #'generate_actions': True
                #}), background=True)

    @property
    def project_dir(self):
        return re.sub(r'[^a-zA-Z0-9]',' ', self.name)

    def commit_in_history(self, ancestor, current):
        """
        Return whether ancestor commit is in the commit history for current commit.
        """
        pass

    def _raw_yaml(self):
        """ Read yaml file defining build """
        with cd(settings.BUILD_ROOT):
            pass

    @property
    def statsd_name(self):
        return statsd_label_converter(self.name)

    def github_push_url(self):
        print self.github_token
        return reverse('github_url', kwargs={'github_token': self.github_token} )

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
        from baleen.action.ssh import RemoteSSHAction
        all_hosts = {}
        for action in self.action_plan():
            if isinstance(action, RemoteSSHAction):
                user_and_host = (action.username, action.host)
                all_hosts.setdefault(user_and_host,[])
                all_hosts[user_and_host].append(action.authorized_keys_entry)
        for user_and_host in all_hosts:
            if include_comments:
                keys = ['## ' + self.name]
                keys.extend(all_hosts[user_and_host])
            all_hosts[user_and_host] = '\n'.join(keys)
        return all_hosts


class Credential(models.Model):
    """
    Used for storing CI credentials related to a project.

    They may be needed by project to run commands on remote hosts, with the
    value being an ssh key, or they may be usernames/passwords for the
    tested projects.

    Credentials must be stored with User or Project.

    ssh key credentials are added temporarily while creating new projects
    to provide a better UX. e.g. when filling in details about the project, the
    user can be prompted to add the public key to github straight away instead
    waiting for a build to fail.
    """
    project = models.ForeignKey('Project', null=True)
    user = models.ForeignKey('auth.User', null=True)
    
    name = models.CharField(max_length=255)
    value = models.TextField(max_length=255)
    environment = models.BooleanField(default=False)

    def __unicode__(self):
        return "Credential: " + self.name

    class Meta:
        unique_together = (('project', 'name'),
                           ('user', 'name'),)


class Hook(models.Model):
    """
    Hooks for success/failure/finished during a build, as
    well as arbitary events.

    """
    project = models.ForeignKey('project.Project')
    # actions can choose to implement any "event", and you can make the hook wait
    # for that.
    watch_for = models.CharField(max_length=255,
            help_text="The event to watch for, can be anything.")

    # Email a user, a particular email address, or the commit author
    email_user = models.ForeignKey('auth.User', null=True, blank=True)
    email_address = models.EmailField(max_length=255, null=True, blank=True)
    email_author = models.BooleanField(default=False)
    
    # Post details about the event
    post_url = models.URLField(default=None, null=True, blank=True)

    trigger_build = models.ForeignKey('project.Project',
            related_name='triggered_by',
            null=True, blank=True)
    one_off = models.BooleanField(default=False)

    def activate(self, *args, **kwargs):
        pass


class BuildDefinition(models.Model):
    """
    A build definition is a file in the repo that is parsed to work out
    how to build the project.

    It is used to generate an ActionPlan.
    """
    project = models.ForeignKey('project.Project')
    #created_at = models.DateTimeField(
            #help_text='The source commit hash this build definition came from')
    commit = models.CharField(max_length=255, null=True, blank=True,
            help_text='The source commit hash this build definition came from')
    filename = models.CharField(max_length=255, null=True, blank=True,
            help_text='Filename will probably help determine what the format is') 
    raw_plan = models.TextField(null=True, blank=True)
    plan_type = models.CharField(max_length=255, null=True, blank=True) 

    def save(self):
        if self.plan_type is None:
            self.plan_type = self.detect_plan_type(self.filename, self.raw_plan)
        super(BuildDefinition, self).save()

    def detect_plan_type(self):
        # assume it's docker until we support new types
        return 'docker'


class ActionResult(models.Model):
    """
    When an Action is run, an ActionResult is created.

    This stores the start time, and when the action finishes, stores the end time
    and status code (0 implies success).

    Any output generated by an action is stored in ActionOutput instances which
    link to an instance of this class.
    """
    job = models.ForeignKey('job.Job')

    action = models.CharField(max_length=255)
    action_slug = models.CharField(max_length=255, blank=True)

    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True)

    status_code = models.IntegerField(null=True)

    message = models.TextField(blank=True)

    def __unicode__(self):
        return "ActionResult for action %s in job %s" % (self.action, self.job.id)

    def save(self):
        self.action_slug = slugify(unicode(self.action))
        super(ActionResult, self).save()

    @property
    def success(self):
        return self.status_code == 0

    @property
    def in_progress(self):
        return self.started_at and self.finished_at is None and self.status_code is None

    @property
    def has_output(self):
        return self.actionoutput_set.count() > 0

    @property
    def stdout(self):
        return self.get_output(output_types.STDOUT)

    @property
    def stderr(self):
        return self.get_output(output_types.STDERR)

    @property
    def duration(self):
        if self.in_progress:
            return None
        return self.finished_at - self.started_at

    def get_output(self, output_type):
        try:
            return self.actionoutput_set.get(output_type=output_type)
        except ActionOutput.DoesNotExist:
            pass
