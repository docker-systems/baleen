import yaml

from StringIO import StringIO

from baleen.utils import statsd_label_converter
from baleen.artifact.models import output_types


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
    def __init__(self, project, name, index, *arg, **kwarg):
        self.project = project
        self.name = name
        self.index = index
        self.outputs = {}

    def __unicode__(self):
        return "Action: %s" % self.name

    def null_action(self, **kwargs):
        """ This is an example for how to implement an Action.
        
        Actions will receive their extra parameters in kwargs.

        Actions are expected to return an ActionResult.
        """
        

    @property
    def statsd_name(self):
        return statsd_label_converter(self.name)

    def execute(self, stdoutlog, stderrlog, action_result):
        return NotImplemented

    def set_output(self, output):
        self.outputs[output.output_type] = output

    def fetch_output(self, o, sftp):
        return NotImplemented

    def as_form_data(self):
        output = {
                'id': self.id,
                'name': self.name,
                'project': self.project.id,
                'index': self.index,
                }
        for output_type, output_full_name in output_types.DETAILS:
            if output_type in output_types.IMPLICIT:
                continue
            output['output_' + output_type] = ''
            o = self.outputs.get(output_type)
            if o:
                output['output_' + output_type] = o.location
        return output

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
        return NotImplemented

    def next(self):
        self.current_index += 1
        return self.plan[self.current_index]


class DockerActionPlan(ActionPlan):

    """Is an iterator that returns BuildSteps"""

    def formulate_plan(self):
        build_data = yaml.load(StringIO(self.build_definition.raw_plan))

        if build_data is None:
            return []
        dependencies = build_data.get('depends', {})
        if dependencies:
            # Then check dependencies and create any missing projects.
            self.get_and_create_projects(dependencies)
            #self.trigger_dependency_builds
            #set up waiting_for if needed, and raise Exception
            pass

        containers_to_build_and_test = build_data['build']

        for c in containers_to_build_and_test:
            #DockerAction()
            pass

        return [
                {
                   'action': 'create_project',
                   'git': 'git@github.com/docker-systems/example-db.git',
                   'project': 'db'
                },
                {
                   'action': 'sync_project',
                   'project': 'db'
                },
                {
                   'action': 'build_project',
                   'project': 'db'
                },
                {
                   'action': 'build_docker_image',
                   'image': 'docker.example.com/blah',
                   'project': 'blah'
                },
                {
                   'action': 'test_docker_image_with_fig',
                   'figfile': 'fig_test.yml',
                   'project': 'blah'
                },
                {
                   'action': 'get_container_artifact',
                   'project': 'blah'
                }
                ]

    def wait_for_project(self, project):
        """
        Tracking when a project is waiting on another one to complete.

        Need to remove all temporary hooks for a given project when that
        project is synced with github (since dependencies may change).
        """
        pass

    def get_and_create_projects(self, deps):
        """
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
        for project_name, val in deps.items():
            src_repo = val.get('src')
            # Check it is actually a repo as opposed to just an image that can
            # be pulled from somewhere:
            if src_repo is None:
                continue

            # check if a project is already using the repo

            # create a new project if not
            projects.append((project_name, val.get('minhash')))
        return projects


    def trigger_dependency_builds(self, projects):
        # check which projects already have a successful build, and trigger builds
        # for those that don't
        for p, minhash in projects:
            j = p.last_successful_job()

            if j and p.commit_in_history(minhash, j.commit):
                # We already have a successful job that is new enough
                continue

            from baleen.job.models import manual_run
            manual_run(p)


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
