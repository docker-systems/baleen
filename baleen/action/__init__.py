import sys
import yaml
import gearman
import json
import logging
import traceback

from django.conf import settings
from StringIO import StringIO
from contextlib import closing

from baleen.utils import statsd_label_converter
from baleen.artifact.models import output_types
from baleen.project.models import Project, Hook


log = logging.getLogger('baleen.action')


class ActionFailure(Exception):
    pass


class Action(object):
    """ Represents one of a series of actions that may be performed after a commit.

    """
    # By default Action base class is not loaded.
    #abstract = True

    def __init__(self, project, name, index, *arg, **kwarg):
        self.project = Project.objects.get(name=project)
        self.name = name
        self.index = index
        self.outputs = {}

    def __unicode__(self):
        return "Action: %s" % self.name

    def send_event_hooks(self, status):
        event = {
            'type': 'action',
            'name': self.name,
            'status': status
        }
        gearman_client = gearman.GearmanClient([settings.GEARMAN_SERVER])
        gearman_client.submit_job(settings.GEARMAN_JOB_LABEL, json.dumps({'event': event}), background=True)

    
    @property
    def statsd_name(self):
        return statsd_label_converter(self.name)

    def run(self, job):
        self.job = job
        log.info("Job %s - doing action: %s - %s" % (unicode(job.id), self.project.name, self.name))

        out_f, err_f = job.get_live_job_filenames()

        with closing(open(out_f, 'w')) as stdoutlog, closing(open(err_f, 'w')) as stderrlog: 
            stdoutlog.write("Project=%s Action=%s\n" % (self.project.name, self.name))
            stdoutlog.flush()

            try:
                # Record that an action is about to be run before executing it.
                # This makes it easier to show actions in progress on the job details/status
                # screens.
                action_result = job.record_action_start(self)

                response = self.execute(stdoutlog, stderrlog, action_result)
            except Exception as e:
                # Any exception that leaks from running the action has stuff recorded
                # and is then raised to the caller
                tb_str = traceback.format_exc(sys.exc_info()[2])
                job.record_action_response(self, {
                    'success': False,
                    'message': str(e),
                    'detail': tb_str 
                })
                log.error("Got an exception %s: %s" % (str(e), tb_str))
                raise ActionFailure(e)

        job.record_action_response(self, response)

        return response

    def execute(self, stdoutlog, stderrlog, action_result):
        """ Execute this Action

        The stdoutlog and stderrlog are file handles for stdout and
        stderr, if you want to record things to a log.

        action_result is an action_result that will have already been created
        and saved to the db prior to this method being called.

        Note that this is usually NOT called directly, it is called via "run".
        "run" will setup the environment for the action to execute in, including
        record ActionResult creation and log files.
        """
        return NotImplemented
    
    def failure_message(self, action_result):
        return 'Action "%s" failed.' % (self.name,)

    def set_output(self, output):
        self.outputs[output.output_type] = output

    def as_form_data(self):
        data = {
                'id': self.id,
                'name': self.name,
                'project': self.project.id,
                'index': self.index,
                }
        for output_type, output_full_name in output_types.DETAILS:
            if output_type in output_types.IMPLICIT:
                continue
            data['output_' + output_type] = ''
            o = self.outputs.get(output_type)
            if o:
                data['output_' + output_type] = o.location
        return data

    def values_without_keys(self):
        data = dict(self.values)
        for k in ['public_key', 'private_key', 'response']:
            if k in data:
                del data[k]
        return data


class ActionPlan(object):

    """Is an iterator that returns Actions """

    def __init__(self, job, project=None):
        """
        Generally ActionPlans should be initialised using a Job's
        build_definition. However, for git repo synchronisation there is none,
        and in this case we just pass the project object directly.
        """
        self.job = job
        self.build_definition = job.build_definition
        if project:
            self.project = project
        else:
            self.project = self.job.project
        self.current_index = -1
        self.plan = []

    def formulate_plan(self):
        """ Return a list of Actions.  """
        return NotImplemented

    def is_blocked(self):
        """ Return whether we are waiting for another dependency to be resolved.  """
        return NotImplemented

    def __iter__(self):
        return self

    def next(self):
        self.current_index += 1
        try:
            return self.plan[self.current_index]
        except IndexError:
            raise StopIteration


class DockerActionPlan(ActionPlan):

    def formulate_plan(self):
        build_data = yaml.safe_load(StringIO(self.build_definition))
        current_project = self.project

        log.debug("Build data for %s is: %s" % (self.project, build_data))

        if build_data is None:
            return []
        dependencies = build_data.get('depends', {})

        # check dependencies
        if dependencies and not self.dependencies_ok(dependencies):
            # create any missing projects, and build them
            dependent_project, plan = self.next_dependency_plan(dependencies)

            if dependent_project is None:
                # TODO: raise an error
                return []

            # set up a trigger for when dependent_project has built
            h = Hook(project=dependent_project, trigger_build=current_project)
            h.save()

            # TODO: Need to remove all temporary hooks for a given project when that
            # project is synced with github (since dependencies may change).
            return plan

        containers_to_build_and_test = build_data['build']
        index=0
        plan = []
        # Unnecessary since we always do a fresh clone now
        #plan.append(
            #{
               #'group': 'project',
               #'action': 'sync_repo',
               #'name': 'Sync project %s with git repo' % self.project.name,
               #'index': index,
               #'project': self.project.name
            #}
        #)
        #index+=1

        for image_name, context in containers_to_build_and_test.iteritems():
            plan.append({
               'group': 'docker',
               'action': 'build_image',
               'name': 'Build docker image %s' % image_name,
               'index': index,
               'image': image_name,
               'context': context,
               'project': self.project.name
            })
            index += 1

        # in the case of any missing projects, the plan returned is one to
        # create/fetch/build one of the dependencies first.
        #
        # whenever the dependencies are not satisfied, the plan will be to
        # try and deal to the dependencies first, while creating a post-success
        # hook waiting for them all.

        plan.append({
                   'group': 'docker',
                   'action': 'test_with_fig',
                   'name': 'Test with fig',
                   'index': index,
                   'fig_data': build_data.get('test'), #'fig_test.yml',
                   'project': self.project.name,
                })
        index += 1

        for artifact_type, details in build_data.get('artifacts', {}).items():
            plan.append({
                       'group': 'docker',
                       'action': 'get_build_artifact',
                       'project':  self.project.name,
                       'name': 'Get build artifact ' + artifact_type,
                       'index': index + 1,
                       'artifact_type': artifact_type,
                       'path': details.get('path')
                    })
            index += 1

        plan.append(
                {
                   'group': 'docker',
                   'action': 'tag_good_image',
                   'project':  self.project.name,
                   'name': 'Tag successfully tested image as "latest"',
                   'index': index
                })
        return plan

    def dependencies_ok(self, dependencies):
        for d_name, d in dependencies.iteritems():
            if not self.check_dependency(repo=d.get('src'), minhash=d.get('minhash')):
                return False
        return True

    def check_dependency(self, repo, minhash=None):
        """
        Check if all project dependencies have a valid build.
        """
        try:
            p = Project.objects.get(repo_url=repo)
        except Project.DoesNotExist:
            return False
        j = p.last_successful_job()

        if j:
            if minhash:
                if p.commit_in_history(minhash, j.commit):
                    # We already have a successful job that is new enough
                    return True
            else:
                return True

        return False

    def next_dependency_plan(self, dependencies):
        """
        Tracking when a project is waiting on another one to complete.

        Deals with this part of the build definition:

        depends:
           rabbitmq:
              src: "git@github.com:docker-systems/rabbitmq.git"
              minhash: "deedbeef" # must have this commit
              # image should be inferred from the baleen.yml of the src repo
              # image: "docker.example.com/rabbitmq"
              #tag: v0.1.1
        """

        projects = []
        for project_name, val in dependencies.items():
            src_repo = val.get('src')
            # Check it is actually a repo as opposed to just an image that can
            # be pulled from somewhere:
            if src_repo is None:
                continue

            # check if a project is already using the repo

            # create a new project if not
            projects.append((project_name, val.get('minhash')))

        # ONLY return a plan with steps if the project isn't already being
        # built
        example_plan = [
                {
                   'group': 'project',
                   'action': 'create',
                   'git': 'git@github.com/docker-systems/example-db.git',
                   'project': 'db'
                },
                {
                   'group': 'project',
                   'action': 'sync',
                   'project': 'db'
                },
                {
                   'group': 'project',
                   'action': 'build',
                   'project': 'db'
                },
                ]

        #return dependent_project, plan
        return None, []


class ExpectedActionOutput(object):
    """ Define expected output from action.

    All Actions produce stdout, stderr, and an exit code.

    Linking ExpectedActionOutput allows for an action to also provide output
    in files or by other mechanisms.

    - 'output_type' is a constant from baleen.artifact.models.output_types
      indicating the type of output.
    - 'location' indicates where the output is available. It's meaning depends
      on the action_type.
      
    """

    def __init__(self, action, output_type, location=None):
        self.action = action
        self.output_type = output_type
        self.location = location

    def __unicode__(self):
        return "Action '%s' expects %s output" % (
                self.action.name,
                self.get_output_type_display(), )

    def get_output_type_display(self):
        res = [x[1] for x in output_types.DETAILS if x[0] == self.output_type]
        if res:
            return res[0]
