import subprocess
import logging
import os

from contextlib import closing
from django.conf import settings

from baleen.action import Action

from baleen.utils import cd


log = logging.getLogger('baleen.action.docker')

def login_registry(registry, creds):
    docker = subprocess.Popen(
        ["docker", "login",
            "-u", creds['user'],
            '-p', creds['password'],
            '-e', creds['email'],
            registry],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
        )

    stdout, stderr = docker.communicate()
    status = docker.returncode
    assert status == 0

    stdout = stdout.decode('utf-8')
    stderr = stderr.decode('utf-8')
    return {
        'stdout': stdout,
        'stderr': stderr,
        'code': status,
    }



def init_actions():
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
        path = os.path.join(settings.BUILD_ROOT, self.project.project_dir)
        with cd(path):
            docker = subprocess.Popen(
                ["docker", "build", "-t", self.image_name + ":baleen", self.context],
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
        self.fig_file = kwarg.get('fig_file')

    def __unicode__(self):
        return "TestWithFigAction: %s" % self.name

    def execute(self, stdoutlog, stderrlog, action_result):
        return {
            'stdout': 'test with fig',
            'stderr': '',
            'code': 0,
        }


class GetBuildArtifactAction(Action):

    def __init__(self, project, name, index, *arg, **kwarg):
        super(GetBuildArtifactAction, self).__init__(project, name, index)
        self.artifact_path = kwarg.get('path')
        self.artifact_type = kwarg.get('artifact_type')
        self.image_name = kwarg.get('image')

    def __unicode__(self):
        return "BuildImageAction: %s" % self.name

    def execute(self, stdoutlog, stderrlog, action_result):
        CONTAINER_NAME = 'monkey'
        path = os.path.join(settings.BUILD_ROOT, self.project.project_dir)
        with cd(path):
            docker = subprocess.Popen(
                ["docker", "cp", CONTAINER_NAME, self.artifact_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
                )

        stdout, stderr = docker.communicate()
        status = docker.returncode

        stdout = stdout.decode('utf-8')
        stderr = stderr.decode('utf-8')
        log.debug(str(self) + 'stdout: %s' % stdout)
        log.debug(str(self) + 'stderr: %s' % stderr)
        return {
            'stdout': stdout,
            'stderr': stderr,
            'code': status,
        }
