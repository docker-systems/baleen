import stat
import logging
import os
import subprocess
import tempfile

from contextlib import closing
from django.conf import settings

from baleen.action import Action

from baleen.utils import mkdir_p, cd


log = logging.getLogger('baleen.action.project')


class CreateAction(Action):
    pass


class GitAction(Action):

    def write_git_wrapper(self, identity_fn):
        fd, git_ssh_fn = tempfile.mkstemp()
        template = """#!/bin/bash\nssh -i %s $@\n"""
        temp_git_wrap = template % identity_fn
        with closing(os.fdopen(fd, 'w')) as tf:
            tf.write(temp_git_wrap)

        # temp file isn't executable by default
        st = os.stat(git_ssh_fn)
        os.chmod(git_ssh_fn, st.st_mode | stat.S_IEXEC)

        return git_ssh_fn

    def write_ssh_identity(self, private_key):
        # This is a little complicated because we want to set up git to use
        # the ssh key for this project. We do this by using the GIT_SSH environment
        # variable, and dumping our private key to a temporary file (that only
        # the current user can read/write)
        fd, identity_fn = tempfile.mkstemp()
        with closing(os.fdopen(fd, 'w')) as tf:
            tf.write(private_key)
        return identity_fn

    def execute(self, stdoutlog, stderrlog, action_result):
        # ensure BUILD_ROOT exists
        mkdir_p(settings.BUILD_ROOT)
        p = self.project

        identity_fn = self.write_ssh_identity(p.private_key)
        git_ssh_fn = self.write_git_wrapper(identity_fn)

        os.environ['GIT_SSH'] = git_ssh_fn
        
        with cd(settings.BUILD_ROOT):
            self.git_action(p)
        del os.environ['GIT_SSH']

        # Clean up after outselves
        os.remove(identity_fn)
        os.remove(git_ssh_fn)


class CloneRepoAction(GitAction):

    def git_action(self, p):
        output = subprocess.Popen(
            ["git", "clone", p.scm_url, p.project_dir],
            stdout=subprocess.PIPE
            ).stdout.read()

        result = output.decode('utf-8')
        log.debug('Git clone stdout: %s' % result)
        return result
 

class SyncRepoAction(GitAction):

    def git_action(self, p):
        with cd(p.project_dir):
            output = subprocess.Popen(
                ["git", "pull", "origin", "master"],
                stdout=subprocess.PIPE
                ).stdout.read()

        result = output.decode('utf-8')
        log.debug('Git pull origin master stdout: %s' % result)
        return result


class BuildAction(Action):
    pass
