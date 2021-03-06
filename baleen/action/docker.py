import subprocess
import logging
import os
import re
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


class ComposeAction(Action):

    def __init__(self, project, name, index, *arg, **kwarg):
        super(ComposeAction, self).__init__(project, name, index)
        self.compose_file = kwarg.get('compose_file')

    def __unicode__(self):
        return "ComposeAction: %s" % self.name

    def execute(self, stdoutlog, stderrlog, action_result):
        pass


class TestWithComposeAction(Action):

    def __init__(self, project, name, index, *arg, **kwarg):
        super(TestWithComposeAction, self).__init__(project, name, index)
        self.compose_raw_data = kwarg.get('compose_data')
        # compose_data looks like:
        #{'subject':
            #{
                #'image':  "docker.domarino.com/api:baleen",
                #'command': ['./run_tests.sh']
            #}
        #}
        self.compose_data = yaml.load(StringIO(self.compose_raw_data))
        self.volume_dir = None

    def _inject_baleen_data(self, data, credentials, stash):
        from baleen.project.models import Credential

        for container in data.keys():
            if 'image' in data[container]:
                image = data[container]['image']
            else:
                image = stash['docker_image']
            image_parts = image.rsplit(':')
            if len(image_parts) > 1:
                image = image_parts[0] 
            data[container]['image'] = image + ':' + stash['docker_tag']

            if credentials:
                data[container].setdefault('environment', {})
                for c_name, value in credentials.items():
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
        return "TestWithComposeAction: %s" % self.name

    def write_compose_file(self, compose_data):
        fd, compose_fn = tempfile.mkstemp()
        with closing(os.fdopen(fd, 'w')) as ft:
            yaml.dump(compose_data, ft)
        log.debug('Wrote Compose test file to %s' % compose_fn)
        return compose_fn

    def execute(self, stdoutlog, stderrlog, action_result):
        build_data = yaml.load(StringIO(self.job.build_definition))

        compose_data_with_images = self._inject_baleen_data(self.compose_data,
                build_data.get('credentials'),
                self.job.stash
                )

        # docker-compore does weird stuff with underscores, dashes, and/or capitals:
        # https://github.com/docker/compose/issues/869
        #
        # e.g. iwmn-js would get turned into iwmnjs as a container name,
        # without any freakin' warning.
        # 
        # strip these characters for now until docker and docker-compose agree
        # on what docker container names should look like
        sanitised_project_name = re.sub("[-_]", "", self.project.name.lower())

        # Set the COMPOSE_PROJECT_NAME environment variable to build id
        # to avoid concurrent builds getting funky:
        # https://github.com/docker/compose/issues/748
        os.environ['COMPOSE_PROJECT_NAME'] = sanitised_project_name + str(self.job.id)

        self.job.stash['compose_project_name'] = os.environ['COMPOSE_PROJECT_NAME']
        self.job.stash['compose_test_container'] = (
                os.environ['COMPOSE_PROJECT_NAME']
                + '_' + 'subject' + '_1' 
                )

        fn = self.write_compose_file(compose_data_with_images)
        compose = subprocess.Popen(
            ["docker-compose", "-f", fn, "up", "-d"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
            )

        stdout, stderr = compose.communicate()
        status = compose.returncode
        
        if status != 0:
            log.debug('"compose up" returned %d' % status)
            return {
                'stdout': stdout,
                'stderr': stderr,
                'code': status,
            }

        # TODO: make collecting the test container logs a separate action
        stdout = stdout.decode('utf-8')
        stderr = stderr.decode('utf-8')
        log.debug('Compose test stdout: %s' % stdout)
        log.debug('Compose test stderr: %s' % stderr)

        # Get test container stdout/stderr
        docker = subprocess.Popen(
            ["docker", "logs", "-f", self.job.stash['compose_test_container'] ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
            )

        log.debug('Using "docker logs -f" to trace test process output')
        stdout, stderr = docker.communicate()
        status = docker.returncode

        if status != 0:
            log.debug('"docker logs -f" returned %d' % status)
            return {
                'stdout': stdout,
                'stderr': stderr,
                'code': status,
            }


        stdout = stdout.decode('utf-8')
        stderr = stderr.decode('utf-8')
        log.debug('docker log stdout: %s' % stdout)
        log.debug('docker log stderr: %s' % stderr)

        # Get test container exit code
        docker2 = subprocess.Popen(
            ["docker", "wait", self.job.stash['compose_test_container'] ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
            )

        log.debug('Using "docker wait" to get return code of test process')
        stdout2, stderr2 = docker2.communicate()
        status = docker2.returncode

        if status != 0:
            log.debug('"docker wait" returned %d' % status)
            return {
                'stdout': stdout2,
                'stderr': stderr2,
                'code': status,
            }

        stdout2 = stdout2.decode('utf-8')
        stderr2 = stderr2.decode('utf-8')
        log.debug('docker wait stdout: %s' % stdout2)
        log.debug('docker wait stderr: %s' % stderr2)

        status = int(stdout2)
        log.debug('Result of compose test was status code %d' % status)

        del os.environ['COMPOSE_PROJECT_NAME']

        return {
            'stdout': stdout,
            'stderr': stderr,
            'code': status,
        }


class GetBuildArtifactAction(Action):

    def __init__(self, project, name, index, *arg, **kwarg):
        super(GetBuildArtifactAction, self).__init__(project, name, index)
        self.artifact_path = kwarg.get('artifact_path')
        self.artifact_type = kwarg.get('artifact_type')

    def __unicode__(self):
        return "GetBuildArtifactAction: %s" % self.name


    def execute(self, stdoutlog, stderrlog, action_result):
        CONTAINER_NAME = self.job.stash['compose_test_container']
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
        log.debug(str(self) + ' stdout: %s' % stdout)
        log.debug(str(self) + ' stderr: %s' % stderr)

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
            p = os.path.join(*p)

            o = CoverageHTMLOutput(action_result=ar, output=p)
            o.save()
        else:
            log.warning("Unknown artifact type %s" % (artifact_type,))


class TagGoodImageAction(Action):

    def __unicode__(self):
        return "TagGoodImageAction: %s" % self.name

    def execute(self, stdoutlog, stderrlog, action_result):
        path = self.job.job_dirs['build']
        with cd(path):
            docker = subprocess.Popen(
                ["docker", "tag", "--force",
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
