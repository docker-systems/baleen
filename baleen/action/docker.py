import subprocess
import logging
import os
import yaml
import tempfile

from StringIO import StringIO
from django.conf import settings
from contextlib import closing

from baleen.action import Action
from baleen.utils import mkdir_p, cd, full_path_split
from baleen.artifact.models import XUnitOutput, CoverageXMLOutput, CoverageHTMLOutput


log = logging.getLogger('baleen.action.docker')


def login_registry(registry, creds):
    """
    Make sure we have logged into a registry using the 
    "docker login" command.
    """
    docker = subprocess.Popen(
        ["docker", "login",
            "-u", creds['user'],
            '-p', creds['password'],
            '-e', creds['email'],
            registry],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
        )

    stdoutdata, stderrdata = docker.communicate()
    status = docker.returncode

    assert status == 0

    stdout = stdoutdata.decode('utf-8')
    stderr = stderrdata.decode('utf-8')
    return {
        'stdout': stdout,
        'stderr': stderr,
        'code': status,
    }


def init_actions():
    """
    init_actions is called when this module is first loaded
    via baleen.action.dispatch.

    We ensure docker host environment variable is setup,
    and that we are signed into any registries that we have
    credentials for.
    """
    os.environ['DOCKER_HOST'] = settings.DOCKER_HOST
    for url, details in settings.DOCKER_REGISTRIES.items():
        login_registry(url, details)


class BuildImageAction(Action):

    def __init__(self, project, name, index, *arg, **kwarg):
        super(BuildImageAction, self).__init__(project, name, index)
        self.context = kwarg.get('context')
        self.image_name = kwarg.get('image')

    def __unicode__(self):
        return "BuildImageAction: %s" % self.name

    def execute(self, stdoutlog, stderrlog, action_result):
        self.docker_tag = 'baleen_' + str(self.job.id)
        self.job.stash['docker_image'] = self.image_name
        self.job.stash['docker_tag'] = self.docker_tag

        path = self.job.job_dirs["build"]
        with cd(path):
            docker = subprocess.Popen(
                ["docker", "build", "-t",
                    self.image_name + ":" + self.docker_tag,
                    self.context],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
                )

        stdout, stderr = docker.communicate()
        status = docker.returncode

        stdout = stdout.decode('utf-8')
        stderr = stderr.decode('utf-8')
        log.debug('BuildImage stdout: %s' % stdout)
        log.debug('BuildImage stderr: %s' % stderr)
        return {
            'stdout': stdout,
            'stderr': stderr,
            'code': status,
        }


class FigAction(Action):

    def __init__(self, project, name, index, *arg, **kwarg):
        super(FigAction, self).__init__(project, name, index)
        self.fig_file = kwarg.get('fig_file')

    def __unicode__(self):
        return "FigAction: %s" % self.name

    def execute(self, stdoutlog, stderrlog, action_result):
        pass


class TestWithFigAction(Action):

    def __init__(self, project, name, index, *arg, **kwarg):
        super(TestWithFigAction, self).__init__(project, name, index)
        self.fig_raw_data = kwarg.get('fig_data')
        # fig_data looks like:
        #{'subject':
            #{
                #'image':  "docker.domarino.com/api:baleen",
                #'command': ['./run_tests.sh']
            #}
        #}
        self.fig_data = yaml.load(StringIO(self.fig_raw_data))
        self.volume_dir = None

    def _inject_baleen_data(self, data):
        from baleen.project.models import Credential

        build_data = yaml.load(StringIO(self.job.build_definition))

        for container in data.keys():
            if 'image' in data[container]:
                image = data[container]['image']
            else:
                image = self.job.stash['docker_image']
            image_parts = image.rsplit(':')
            if len(image_parts) > 1:
                image = image_parts[0] 
            data[container]['image'] = image + ':' + self.job.stash['docker_tag']

            if 'credentials' in build_data:
                data[container].setdefault('environment', {})
                for c_name, value in build_data['credentials'].items():
                    try:
                        c = Credential.objects.get(project=self.project, name=c_name)
                        val = c.value
                    except Credential.DoesNotExist:
                        log.warning('No credential found with name %s' % c_name)
                        val = None
                    if value == 'FILE':
                        # TODO write credential to image using:
                        # echo val | docker run -i DOCKER_IMAGE /bin/bash -c 'cat > tempfilename'
                        # docker commit `docker ps -l -q` DOCKER_IMAGE:docker_tag+"credential"
                        # val == 'tempfilename'
                        pass
                    data[container]['environment'][c_name] = val
        return data

    def __unicode__(self):
        return "TestWithFigAction: %s" % self.name

    def write_fig_file(self, fig_data):
        fd, identity_fn = tempfile.mkstemp()
        with closing(os.fdopen(fd, 'w')) as ft:
            yaml.dump(fig_data, ft)
        return identity_fn

    def execute(self, stdoutlog, stderrlog, action_result):
        fig_data_with_images = self._inject_baleen_data(self.fig_data)
        # Set the FIG_PROJECT_NAME environment variable to build id
        # to avoid concurrent builds getting funky:
        # https://github.com/docker/fig/issues/748
        os.environ['FIG_PROJECT_NAME'] = self.project.name + str(self.job.id)

        self.job.stash['fig_project_name'] = os.environ['FIG_PROJECT_NAME']
        self.job.stash['fig_test_container'] = (
                os.environ['FIG_PROJECT_NAME']
                + '_' + 'subject' + '_1' 
                )

        fn = self.write_fig_file(fig_data_with_images)
        fig = subprocess.Popen(
            ["fig", "-f", fn, "up", "-d"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
            )

        stdout, stderr = fig.communicate()
        status = fig.returncode
        
        if status != 0:
            return {
                'stdout': stdout,
                'stderr': stderr,
                'code': status,
            }

        # TODO: make collecting the test container logs a separate action
        stdout = stdout.decode('utf-8')
        stderr = stderr.decode('utf-8')
        log.debug('Fig test stdout: %s' % stdout)
        log.debug('Fig test stderr: %s' % stderr)

        # Get test container stdout/stderr
        docker = subprocess.Popen(
            ["docker", "logs", "-f", self.job.stash['fig_test_container'] ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
            )

        stdout, stderr = docker.communicate()
        status = docker.returncode

        if status != 0:
            return {
                'stdout': stdout,
                'stderr': stderr,
                'code': status,
            }


        stdout = stdout.decode('utf-8')
        stderr = stderr.decode('utf-8')
        log.debug('Get test stdout: %s' % stdout)
        log.debug('Get test stderr: %s' % stderr)

        # Get test container exit code
        docker2 = subprocess.Popen(
            ["docker", "wait", self.job.stash['fig_test_container'] ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
            )

        stdout2, stderr2 = docker2.communicate()
        status = docker2.returncode

        if status != 0:
            return {
                'stdout': stdout2,
                'stderr': stderr2,
                'code': status,
            }

        stdout2 = stdout2.decode('utf-8')
        stderr2 = stderr2.decode('utf-8')
        log.debug('Get test stdout: %s' % stdout2)
        log.debug('Get test stderr: %s' % stderr2)

        status = int(stdout2)

        del os.environ['FIG_PROJECT_NAME']

        return {
            'stdout': stdout,
            'stderr': stderr,
            'code': status,
        }


class GetBuildArtifactAction(Action):

    def __init__(self, project, name, index, *arg, **kwarg):
        super(GetBuildArtifactAction, self).__init__(project, name, index)
        self.artifact_path = kwarg.get('path')
        self.artifact_type = kwarg.get('artifact_type')

    def __unicode__(self):
        return "BuildImageAction: %s" % self.name

    def execute(self, stdoutlog, stderrlog, action_result):
        CONTAINER_NAME = self.job.stash['fig_test_container']
        path = self.job.job_dirs['artifact']
        mkdir_p(path)

        docker = subprocess.Popen(
                ["docker", "cp",
                    CONTAINER_NAME + ":" + self.artifact_path,
                    path
                ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
            )

        stdout, stderr = docker.communicate()
        status = docker.returncode

        stdout = stdout.decode('utf-8')
        stderr = stderr.decode('utf-8')
        log.debug(str(self) + 'stdout: %s' % stdout)
        log.debug(str(self) + 'stderr: %s' % stderr)

        if status == 0:
            self.record_artifact(
                    action_result,
                    self.artifact_type,
                    os.path.join(path, os.path.basename(self.artifact_path))
                )

        return {
            'stdout': stdout,
            'stderr': stderr,
            'code': status,
        }

    def record_artifact(self, ar, artifact_type, path):
        if artifact_type == 'xunit':
            with open(path, 'r') as f:
                o = XUnitOutput(action_result=ar, output=f.read())
                o.save()
        elif artifact_type == 'coverage':
            with open(path, 'r') as f:
                o = CoverageXMLOutput(action_result=ar, output=f.read())
                o.save()
        elif artifact_type == 'coverage_html':
            p = full_path_split(path)[-3:]
            print('coverage html path is ' + str(p))
            p = os.path.join(p)

            o = CoverageHTMLOutput(action_result=ar, output=p)
            o.save()


class TagGoodImageAction(Action):

    def __unicode__(self):
        return "TagGoodImageAction: %s" % self.name

    def execute(self, stdoutlog, stderrlog, action_result):
        path = self.job.job_dirs['build']
        with cd(path):
            docker = subprocess.Popen(
                ["docker", "tag",
                    self.job.stash['docker_image'] + ":" +
                    self.job.stash['docker_tag'],
                    self.job.stash['docker_image'] + ":latest",
                    ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
                )

        stdout, stderr = docker.communicate()
        status = docker.returncode

        stdout = stdout.decode('utf-8')
        stderr = stderr.decode('utf-8')
        log.debug('BuildImage stdout: %s' % stdout)
        log.debug('BuildImage stderr: %s' % stderr)
        return {
            'stdout': stdout,
            'stderr': stderr,
            'code': status,
        }


