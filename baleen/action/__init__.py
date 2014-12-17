import yaml
import gearman
import json

from django.conf import settings
from StringIO import StringIO

from baleen.utils import statsd_label_converter
from baleen.artifact.models import output_types
from baleen.project.models import Project, Hook


def parse_build_definition(bd):
    """
    Work out what kind of build definition we're working with and return
    the appropriate ActionPlan instance.
    """
    plan_type = bd.detect_plan_type()
    if plan_type == 'docker':
        plan = DockerActionPlan(bd)
    else:
        return NotImplemented

    return plan.formulate_plan()


class Action(object):
    """ Represents one of a series of actions that may be performed after a commit.

    """
    # By default Action base class is not loaded.
    #abstract = True

    def __init__(self, project, name, index, *arg, **kwarg):
        self.project = project
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

    def execute(self, stdoutlog, stderrlog, action_result):
        """ Execute this Action

        The stdoutlog and stderrlog are file handles for stdout and
        stderr, if you want to record things to a log.

        action_result is an action_result that will have already been created
        and saved to the db prior to this method being called.
        """
        return NotImplemented

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

    def __init__(self, build_definition):
        self.build_definition = build_definition
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

    """Is an iterator that returns BuildSteps"""

    def formulate_plan(self):
        build_data = yaml.load(StringIO(self.build_definition.raw_plan))
        current_project = self.build_definition.project

        if build_data is None:
            return []
        dependencies = build_data.get('depends', {})

        # check dependencies
        if dependencies and not self.dependencies_ok(dependencies):
            # create any missing projects, and build them
            dependent_project, plan = self.next_dependency_plan(dependencies)

            # set up a trigger for when dependent_project has built
            h = Hook(project=dependent_project, trigger_build=current_project)
            h.save()

            # TODO: Need to remove all temporary hooks for a given project when that
            # project is synced with github (since dependencies may change).
            return plan

        containers_to_build_and_test = build_data['build']

        for c in containers_to_build_and_test:
            #DockerAction()
            pass

        # in the case of any missing projects, the plan returned is one to
        # create/fetch/build one of the dependencies first.
        #
        # whenever the dependencies are not satisfied, the plan will be to
        # try and deal to the dependencies first, while creating a post-success
        # hook waiting for them all.

        plan = [
                {
                   'group': 'docker',
                   'action': 'build_image',
                   'image': 'docker.example.com/blah',
                   'project': 'blah'
                },
                {
                   'group': 'docker',
                   'action': 'test_with_fig',
                   'figfile': 'fig_test.yml',
                   'project': 'blah'
                },
                {
                   'group': 'docker',
                   'action': 'get_build_artifact',
                   'project': 'blah'
                }
                ]
        return plan

    def dependencies_ok(self, dependencies):
        for d in dependencies:
            if not self.check_dependency(repo=d.get('src'), minhash=d.get('minhash')):
                return False
        return True

    def check_dependency(self, repo, minhash=None):
        """
        Check if all project dependencies have a valid build.
        """
        try:
            p = Project.objects.get(scm_url=repo)
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
        print(example_plan)

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

