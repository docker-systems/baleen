import time
import os
import paramiko
import subprocess
import tempfile

from django.conf import settings
from contextlib import closing

from stat import S_ISDIR
from StringIO import StringIO

from baleen.action import Action

from baleen.artifact.models import output_types, ActionOutput

from baleen.utils import get_credential_key_pair


class RemoteSSHAction(Action):
    """
    Abstract action to do something on a remote host with ssh access.

    TODO: There are some less than stellar security issues here:
    - the input from user is not sanitised, and it is used to
      construct entires for authorized_keys.
    - when executing the action, it auto accepts and allows unknown and
      missing host keys.
    - when we expect an 'output' file from the action, we need to relax
      the permissions on that host so that baleen has general shell access
      to the host. See the authorized_keys_entry property for more info and
      a possible way to restrict access while still allowing scp to function.
    """
    # Don't treat this as an actual action
    abstract = True

    def __init__(self, project, name, index, *arg, **kwarg):
        super(RemoteSSHAction, self).__init__(project, name, index)

        self.username = kwarg.get('username')
        self.host = kwarg.get('host')

        credential_name = '%s@%s' % (self.username, self.host)
        self.private_key, self.public_key = get_credential_key_pair(
                credential_name,
                project=self.project
                )

    def __unicode__(self):
        return "RemoteSSHAction: %s" % self.name

    @property
    def authorized_keys_entry(self):
        # We limit this action to a single command on the destination
        # host.
        #
        # TODO Need to escape double quotes!
        key_entry = '# ' + (self.name or '') + '\n'
        # Can we reenable limiting the ssh command based on key? Need
        # to differentiate between running a command and copying a file.
        #action_command += '\ncommand="%s",' % self.command
        key_entry += 'no-agent-forwarding,no-port-forwarding,no-pty,no-X11-forwarding %s' % self.public_key.value
        return key_entry

    @property
    def host_address(self):
        """
        Resolve host into a valid address. Currently this is a wrapper to
        extract the current lxc container ip lease.
        """
        if self.host and self.host.startswith('lxc:'):
            # This doesn't check that the LXC is actually running
            # Translate lxc name into ip addr
            lxc_name = self.host[(self.host.index(':') + 1):]
            p = subprocess.Popen(
                    "cat /var/lib/misc/dnsmasq.leases | grep ' %s ' | awk '{print $3}'" % lxc_name,
                    shell=True,
                    stdout=subprocess.PIPE
                    )
            stdout, stderr = p.communicate()
            if stdout:
                return stdout.strip()
        return self.host

    def get_ssh_connection(self):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        ssh.connect(
            self.host_address,
            username = self.username,
            pkey = paramiko.RSAKey.from_private_key(StringIO(self.private_key.value)),
            allow_agent = False,
            look_for_keys = False,
        )

        return ssh

    def as_form_data(self):
        output = super(RemoteSSHAction, self).as_form_data()

        output.update({
                'username': self.username,
                'command': self.command,
                'host': self.host,
                'authorized_keys_entry': self.authorized_keys_entry,
                })
        return output


class RunCommandAction(RemoteSSHAction):
    label = 'run_command'

    STREAM_BUFFER_SIZE = 1048576

    def __init__(self, *arg, **kwarg):
        super(RunCommandAction, self).__init__(*arg, **kwarg)

        self.command = kwarg.get('command')

    def execute(self, stdoutlog, stderrlog, action_result):
        try:
            with closing(self.get_ssh_connection()) as ssh:
                transport = ssh.get_transport()

                response = self._run_command(self.command, transport,
                        stdoutlog, stderrlog,
                        action_result)
        except AuthenticationException:
            job.record_action_response(action, {
                'success': False,
                'message': "Authentication failure. Have you checked the host's .ssh/authorized_keys2 is up to date?",
            })
            stdoutlog.close()
            stderrlog.close()
            raise ActionFailed()
        return response

    def _run_command(self, command, transport, stdoutlog=None, stderrlog=None, action_result=None):
        response = {'stdout': '', 'stderr': '', 'code': None}

        chan = transport.open_session()
        chan.exec_command(command)

        a_stdout = ActionOutput(action_result=action_result,
                output_type=output_types.STDOUT) if action_result else None
        a_stderr = ActionOutput(action_result=action_result,
                output_type=output_types.STDERR) if action_result else None

        def save_stream(data, action_output, log):
            if log:
                log.write(data)
                log.flush()
            if action_output:
                if action_output.output is None:
                    action_output.output = ''

                action_output.output += data
                action_output.save()
            return data

        buff_size = self.STREAM_BUFFER_SIZE

        while not chan.exit_status_ready():
            time.sleep(1)
            if chan.recv_ready():
                response['stdout'] += save_stream(chan.recv(buff_size), a_stdout, stdoutlog)
            if chan.recv_stderr_ready():
                response['stderr'] += save_stream(chan.recv_stderr(buff_size), a_stderr, stderrlog)

        # Read any remaining data in the streams
        while chan.recv_ready():
            response['stdout'] += save_stream(chan.recv(buff_size), a_stdout, stdoutlog)
        while chan.recv_stderr_ready():
            response['stderr'] += save_stream(chan.recv_stderr(buff_size), a_stderr, stderrlog)

        response['code'] = chan.recv_exit_status()
        return response


class FetchFileAction(RemoteSSHAction):
    """
    Fetch a individual file or directory from a remote host.

    Output locations are presumed to be accessable via scp.

    scp -v -f -- src_file
    """
    label = 'fetch_file'

    def __init__(self, *arg, **kwarg):
        super(FetchFileAction, self).__init__(*arg, **kwarg)

        self.path_to_fetch = kwarg['path']
        self.path_is_dir = kwarg.get('is_dir', False)

    def execute(self, stdoutlog, stderrlog, action_result):
        with closing(self.get_ssh_connection()) as ssh:
            transport = ssh.get_transport()

            # TODO: catch sftp errors
            sftp = paramiko.SFTPClient.from_transport(transport)

            response = self.fetch_output(self.path_to_fetch, self.path_is_dir, sftp)
        return response

    def _copy_dir(self, sftp, src, dest):
        file_list = sftp.listdir(path=src)
        for f in file_list:
            src_f = os.path.join(src,f)
            dest_f = os.path.join(dest,f)
            if S_ISDIR(sftp.stat(src_f).st_mode):
                os.mkdir(os.path.join(dest,f))
                self._copy_dir(sftp, src_f, dest_f)
            sftp.get(remotepath=src_f, localpath=dest_f)

    def fetch_output(self, p, is_dir, sftp):
        # Assume that default directory is home of the login user
        location = p.replace('~', sftp.normalize('.'))

        stat = sftp.stat(location)
        if not stat:
            return None

        # manually split instead of using python os.path.basename because
        # might be a dir with trailing slash
        basename = os.path.split(location)[-1]
        dest = tempfile.mkdtemp(prefix=basename, dir=settings.ARTIFACT_DIR)

        if is_dir:
            assert S_ISDIR(stat.st_mode)
            self._copy_dir(sftp, location, dest)
            local_path = dest
        else:
            if S_ISDIR(stat.st_mode):
                return None
            local_path = os.path.join(dest, basename)
            sftp.get(remotepath=location, localpath=local_path)

            # Code to read the file directly:
            ## to copy file from remote to local
            #f = sftp.open(location)
            #content = f.read()
            #f.close()
            #return content
        return local_path
