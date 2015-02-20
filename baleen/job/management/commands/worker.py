import os
import logging
import sys
import traceback
import gearman
import json
import functools

from optparse import make_option
from signal import signal, SIGTERM, SIGINT

from django.conf import settings
from django.core.management.base import BaseCommand

from baleen.job.models import Job
from baleen.project.models import ActionResult, Project
from baleen.action.dispatch import get_action_object
from baleen.utils import mkdir_p, cd

import statsd
from statsd.counter import Counter
from statsd import Timer

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger('baleen.worker')

statsd.Connection.set_defaults(host='localhost', port=8125, sample_rate=1, disabled=True)

class BaleenGearmanWorker(gearman.GearmanWorker):
    def on_job_execute(self, current_job):
        print "Job started"
        return super(BaleenGearmanWorker, self).on_job_execute(current_job)

    def on_job_exception(self, current_job, exc_info):
        result = str(exc_info)
        return super(BaleenGearmanWorker, self).send_job_complete(
                current_job, result)

    def on_job_complete(self, current_job, job_result):
        return super(BaleenGearmanWorker, self).send_job_complete(
                current_job, job_result)

    def after_poll(self, any_activity):
        # Return True if you want to continue polling, replaces callback_fxn
        return True

gearman_worker = BaleenGearmanWorker([settings.GEARMAN_SERVER])

class Command(BaseCommand):
    help = """
"""
    option_list = BaseCommand.option_list + (
            make_option('-p', '--procnum',
                default='0',
                action='store',
                dest='worker_number',
                help="Worker number"
            ),
            make_option('-c', '--clear',
                default=False,
                action='store_true',
                dest='clear_jobs',
                help="Clear all jobs in queue, don't run them."
            ),
            make_option('-b', '--build',
                default=None,
                action='store',
                dest='build',
                help="Take a directory with a baleen.yml and build it."
            ),
        )

    def _reset_jobs(self):
        self.current_gearman_job = None
        self.current_baleen_job = None
        self.current_action = None

    def _get_statsd_counters(self, project):
        return {
                'project': {
                    'deploys': Counter('baleen.%s.deploy_count' % project.statsd_name),
                    'success': Counter('baleen.%s.success_count' % project.statsd_name),
                },
                'all': {
                    'deploys': Counter('baleen.all.deploy_count'),
                    'success': Counter('baleen.all.success_count'),
                }
                # TODO: can't track correctly by user until github names are connected to baleen
                # users
                #'user': { 
                    #'deploys': Counter('baleen.all.deploy_count' % project.statsd_name),
                    #'success': Counter('baleen.all.failure_count' % project.statsd_name),
                #}
        }


    def run_task(self, worker, gm_job):
        try:
            self.current_gearman_job = gm_job
            task_data = json.loads(gm_job.data)
            if task_data.get('job'):
                job_id = task_data.get('job')
                return self.run_job(job_id)
            else:
                return "Unknown task type"
            print 'Task complete!'
        except Exception, e:
            msg = "Unexpected error:" + sys.exc_info()[0]
            msg += str(e)
            print msg
            traceback.print_tb(sys.exc_info()[2])

            self.clear_current_action(msg)
            self._reset_jobs()
        return ''

    def _do_action(self, job, action, project_timer=None):
        # record this process id so that we can kill it via the web interface
        # supervisord will automatically create a replacement process.

        log.debug("Doing action %s" % action)
        a = get_action_object(action)
        self.current_action = a
        response = a.run(job)
        log.debug("Action completed with response %s" % str(response))
        self.current_action = None

        if response['code'] != 0:
            # If we got a non-zero exit status, then don't run any more actions
            raise Exception('Non-zero exit code')

        if project_timer:
            project_timer.intermediate(a.statsd_name)
        print "Action success."


    def run_job(self, job_id):
        worker_pid = os.getpid()
        job = Job.objects.get(id=job_id)

        self.current_baleen_job = job

        print "Running job %s" % job_id

        # Only one job per project!  Until we have per-project queues,
        # just reject this job if there's already another one running
        # for the same project.
        if job.project.current_job():
            print "Job already in progress!"
            job.reject()
            self._reset_jobs()
            return ''

        # Get statsd connections
        project_t = Timer('baleen.%s.duration' % job.project.statsd_name)
        all_t = Timer('baleen.all.duration')

        counters = self._get_statsd_counters(job.project)
        counters['project']['deploys'] += 1
        counters['all']['deploys'] += 1

        project_t.start()
        all_t.start()
        job.record_start(worker_pid)

        sync_actions = job.checkout_repo_plan()
        for action in sync_actions:
            self._do_action(job, action, project_t)

        print "Finished sync with git"

        actions = job.project.action_plan()
        for action in actions:
            self._do_action(job, action, project_t)

        job.record_done()
        all_t.stop()
        project_t.stop()
        counters['project']['success'] += 1
        counters['all']['success'] += 1
        self._reset_jobs()

        print "Job completed."
        # Return empty string since this is always invoked in background mode, so
        # no-one would see the response anyway
        return ''

    def handle(self, *args, **options):
        self.current_gearman_job = None
        self.current_baleen_job = None
        self.current_action = None

        self.worker_process_number = options['worker_number']

        signal(SIGTERM, self.clean_up)
        signal(SIGINT, self.clean_up)

        if options['build']:
            self.build(options['build'])
            sys.exit(0)
        elif options['clear_jobs']:
            print "Removing all jobs in queue..."
            gearman_worker.register_task(settings.GEARMAN_JOB_LABEL, functools.partial(self.clear_job))
        else:
            # Default is to wait for jobs
            gearman_worker.register_task(settings.GEARMAN_JOB_LABEL, functools.partial(self.run_task))

        print "baleen worker reporting for duty, sir/m'am!"
        gearman_worker.work()

    def clear_job(self, worker, gm_job):
        job_id = json.loads(gm_job.data).get('job_id', None)
        result = "Clearing job for job_id %d" % str(job_id)
        return result

    def build(self, build_dir):
        p = None
        project_name = None
        counter = 1
        while p is None:
            project_name = os.path.basename(build_dir) + str(counter)
            try:
                Project.objects.get(name=project_name)
                counter += 1
            except Project.DoesNotExist:
                p = Project(name=project_name)
            if counter > 100:
                raise Exception("Can't find a free project name.")
        p.save()
        job = Job(project=p, manual_by=p.creator)
        job.save()

        self.current_baleen_job = job

        try:
            job._job_dirs = {
                    'build': build_dir,
                    'artifact': os.path.join('/tmp/', project_name),
                    'logs': os.path.join('/tmp/', project_name),
                    'checkout': None
                    }
            job.record_start(os.getpid())

            # import baleen file
            import_action_spec = {
                   'group': 'project',
                   'action': 'import_build_definition',
                   'name': 'Import build definition for project %s' % p.name,
                   'index': 1,
                   'project': p.name
                }
            self._do_action(job, import_action_spec)

            actions = job.project.action_plan()
            for action in actions:
                self._do_action(job, action)

            job.record_done()
            self._reset_jobs()

            print "Job completed."
        except Exception, e:
            msg = "Unexpected error:" + str(sys.exc_info()[0])
            msg += str(e)
            print msg
            traceback.print_tb(sys.exc_info()[2])

            self.clear_current_action(msg)
            self._reset_jobs()

        p.delete()


    def clear_current_action(self, msg=None):
        if self.current_action:
            print "have action, record action response"
            if msg is None:
                msg = "Action was interrupted by kill/term signal."

            try:
                self.current_baleen_job.record_action_response(self.current_action, {
                    'success': False,
                    'message': msg,
                })
            except ActionResult.DoesNotExist:
                self.current_baleen_job.record_done(success=False)
        elif self.current_baleen_job:
            print "no action, just done"
            self.current_baleen_job.record_done(success=False)

    def clean_up(self, *args):
        print "Exiting, please wait while we update job status"
        if self.current_baleen_job:
            self.clear_current_action()
        if self.current_gearman_job:
            # We need to tell gearman to forget about this job
            gearman_worker.send_job_complete(self.current_gearman_job, data='')
        self._reset_jobs()
        sys.exit(1)
