import os
import json
import gearman
import signal
import requests

from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.utils.timezone import now

from baleen.artifact.models import ActionOutput, output_types

from jsonfield import JSONField


def manual_run(project, user=None):
    """ Manually instantiate a job for project """
    last_j = project.last_job()
    if last_j and last_j.github_data:
        blank_job = Job(project=last_j.project, github_data=last_j.github_data)
    elif user:
        blank_job = Job(project=project, manual_by=user)
    else:
        blank_job = Job(project=project, manual_by=project.creator)
    blank_job.save()
    blank_job.submit()
    return blank_job


class Job(models.Model):
    project = models.ForeignKey('project.Project')
    github_data = JSONField()

    commit = models.CharField(max_length=255, null=True, blank=True)
    received_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    success = models.BooleanField(default=False)
    manual_by = models.ForeignKey(User, null=True, blank=True)

    rejected = models.BooleanField(default=False)
    worker_pid = models.IntegerField(null=True, blank=True)

    def __unicode__(self):
        return "Job for '%s' at %s" % (self.project.name, unicode(self.received_at))

    def submit(self):
        """ Send job to gearman """
        gearman_client = gearman.GearmanClient([settings.GEARMAN_SERVER])
        gearman_client.submit_job(settings.GEARMAN_JOB_LABEL, json.dumps({'job': self.id}), background=True)

    def record_action_start(self, action):
        from baleen.project.models import ActionResult
        a = ActionResult(action=action, job=self, started_at=now())
        a.save()
        return a

    def record_action_response(self, action, response):
        from baleen.project.models import ActionResult
        a = ActionResult.objects.get(action=action, job=self)

        a.status_code = response.get('code')
        if a.status_code is None:
            if not response.get('success', True):
                a.status_code = -1
            else:
                raise RuntimeWarning("Set success to true but didn't set status_code")

        for h in response.get('hooks', []):
            # TODO: support recording the output from running hooks
            #raise Exception('Support hooks')
            pass

        a.finished_at = now()

        # Handle adding a summary message
        if not a.success:
            a.message = 'Command "%s" on "%s@%s" failed with exit code: %d' % (
                    action.command, action.username, action.host, a.status_code)
        a.message += response.get('message', '')

        if not a.success:
            # If a action belonging to this job fails, then the whole job is marked
            # unsuccessful
            self.record_done(success=False)

        a.save()

        for stdio, out_type in (('stderr', output_types.STDERR), ('stdout', output_types.STDOUT)):
            a_std, created = ActionOutput.objects.get_or_create(action_result=a, output_type=out_type)
            a_std.output=response.get(stdio,'')
            a_std.save()

        for output_type, the_output in response.get('output', {}).items():
            # Check we are expecting output for this action
            ao = ActionOutput(output=the_output, action_result=a, output_type=output_type)
            ao.save()

        return a

    def record_start(self, pid):
        """ Indicate that this job is going to now be run. It is active.

        In the ideal case job's action history will always be blank when
        starting, however, if the worker is killed then gearman never knows
        about the job being completed.

        Either way probably should explicitly clear the job action history.
        """
        self.started_at = now()
        self.actionresult_set.all().delete() # delete all old action results
        self.success = False
        self.worker_pid = pid
        self.finished_at = None
        self.save()

    def record_done(self, success=True):
        self.success = success
        self.finished_at = now()
        self.worker_pid = None
        self.save()
        if not success:
            commits = self.github_data.get('commits')
            if commits is None:
                return
            emails = [c['author']['email'] for c in commits]  # could use committer instead of author
            compare = self.github_data.get('compare')
            name = self.github_data.get('repository')['name']
            requests.post(
                settings.MAILGUN_URL,
                auth=("api", settings.MAILGUN_KEY),
                data={"from": settings.BALEEN_EMAIL,
                      "to": emails,
                      "subject": "Baleen is angry with you",
                      "text": "One of these commits %s has broken %s!" % (compare, name)})

    @property
    def done(self):
        return self.finished_at is not None

    def reject(self):
        self.started_at = now()
        self.finished_at = now()
        self.rejected = True
        self.success = False
        self.save()

    def kill(self):
        try:
            if self.finished_at == None and self.worker_pid:
                os.kill(self.worker_pid, signal.SIGTERM)
        except OSError:
            # Usually this means the process no longer exists
            # Or we have no permission to kill it
            pass
        self.record_done(success=False)

    def get_live_job_filenames(self):
        p = self.project
        log_dir = os.path.join(settings.PROJECT_DIR, 'logs')
        out_f = os.path.join(log_dir, '%s-%s-stdout.log' % (p.name, p.id))
        err_f = os.path.join(log_dir, '%s-%s-stderr.log' % (p.name, p.id))
        return out_f, err_f

    def get_action_result_with_output(self, output_type):
        action_output = ActionOutput.objects.filter(
                    output_type=output_type,
                    action_result__job=self
                ).order_by('action_result__started_at').first()
        if action_output:
            return action_output.action_result

    def test_action_result(self):
        return self.get_action_result_with_output(output_types.XUNIT)

    @property
    def current_action(self):
        return self.actionresult_set.order_by('-started_at').first()

    @property
    def ordered_actions(self):
        return self.actionresult_set.order_by('started_at')
