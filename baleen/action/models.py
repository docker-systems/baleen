import time
import paramiko
import operator
import subprocess

from baleen.utils import statsd_label_converter, generate_ssh_key
from StringIO import StringIO

from django.db import models

from baleen.utils import ManagerWithFirstQuery
from baleen.artifact.models import ExpectedActionOutput, output_types, ActionOutput


class Hook(models.Model):
    # TODO: refactor the concept of a Command out of Action.
    # TODO: Potentially use django signals?
    #
    # Hooks for success/failure/finished after an action
    project = models.ForeignKey('project.Project')
    action = models.ForeignKey('Action', blank=True, null=True)
    command = models.TextField()

    SUCCESS = 'S'
    FAILURE = 'X'
    DONE = 'D'
    HOOK_TRIGGERS = (
        (SUCCESS, 'Success'),
        (FAILURE, 'Failure'),
        (DONE, 'Done'),
    )
    hook_trigger = models.CharField(max_length=1, choices=HOOK_TRIGGERS, default=DONE)


class Action(models.Model):
    """ Represents one of a series of actions that may be performed after a commit.

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
    project = models.ForeignKey('project.Project')
    index = models.IntegerField()
    name = models.CharField(max_length=64, default='noname')

    username = models.CharField(max_length=64)
    host = models.CharField(max_length=255)
    command = models.TextField()

    enabled = models.BooleanField(default=True, blank=True)

    # Output is the locations for various output files that baleen knows how to read.
    # action.valid_output_tags has a list.
    public_key = models.TextField(editable=False)
    private_key = models.TextField(editable=False)

    def __unicode__(self):
        return "Action: %s" % self.name

    def save(self):
        if (not self.private_key or not self.public_key):
            self.private_key, self.public_key = generate_ssh_key()
        super(Action, self).save()

    @property
    def statsd_name(self):
        return statsd_label_converter(self.name)

    @property
    def authorized_keys_entry(self):
        action_command = '# ' + (self.name or '')
        has_outputs = self.expectedactionoutput_set.all()
        if has_outputs.count() == 0:
            # We can only limit this action to a single command on the destination
            # host if we don't need to retrieve the results after.

            # TODO Need to escape double quotes!
            action_command += '\ncommand="%s",' % self.command
        else:
            # We could theoretically create keys for the output and limit access
            # using the a technique like:
            #   http://sange.fi/~atehwa/cgi-bin/piki.cgi/restricting%20scp%20on%20per-user%20basis
            # However, this requires the addition of a scp_wrapper script to the destination
            # host and in this case, we opt for convenience over rigid security.
            # (however this is for scp, and we use paramiko's sftp client which
            # I don't know the details of)
            locations = [x['location'] for x in has_outputs.values('location')]
            action_command += ' and for fetching output %s\n' % (','.join(locations))
        action_command += 'no-agent-forwarding,no-port-forwarding,no-pty,no-X11-forwarding %s' % self.public_key
        return action_command

    @property
    def host_address(self):
        if self.host.startswith('lxc:'):
            # This doesn't check that the LXC is actually running
            # TODO: check lxc is running

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

    def execute(self, stdoutlog, stderrlog, action_result):
        ssh = paramiko.SSHClient()
        # TODO - autoadd is evil!
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            self.host_address,
            username = self.username,
            pkey = paramiko.RSAKey.from_private_key(StringIO(self.private_key)),
            allow_agent = False,
            look_for_keys = False,
        )
        transport = ssh.get_transport()
        response = self._run_command(self.command, transport,
                stdoutlog, stderrlog,
                action_result)

        response['hooks'] = self.run_hooks(response['code'], transport)

        if self.expectedactionoutput_set.count() > 0:
            sftp = paramiko.SFTPClient.from_transport(transport)
            response['output'] = {}
            for o in self.expectedactionoutput_set.all():
                response['output'][o.output_type] = o.fetch(sftp)

        ssh.close()

        return response

    def _run_command(self, command, transport, stdoutlog=None, stderrlog=None, action_result=None):
        response = {'stdout': '', 'stderr': '', 'code': None}

        chan = transport.open_session()
        chan.exec_command(command)

        buff_size = 1048576

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

    def run_hooks(self, status_code, transport):
        h_result = {}
        if self.hook_set.count() == 0:
            return h_result
        for h in self.hook_set.all():
            if status_code != 0:
                # non zero exit considered failure
                if h.hook_trigger in [Hook.FAILURE, Hook.DONE]:
                    h_result[h.hook_trigger] = self._run_command(h.command, transport)
            elif h.hook_trigger in [Hook.SUCCESS, Hook.DONE]:
                h_result[h.hook_trigger] = self._run_command(h.command, transport)
        return h_result

    def set_output(self, output_type, location):
        """ Define expected output from action.

        All Actions produce stdout, stderr, and an exit code.

        Linking ExpectedActionOutput allow for an action to also provide output
        in files or by other mechanisms.

        - 'output_type' is a constant from baleen.action.models.output_types
          indicating the type of output.
        - 'location' indicates where the output is available. It is presumed to be
          accessable via scp.

        scp -v -f -- src_file

        Output also includes ssh key pair to allow scp to work.

        """
        if not output_type:
            return
        assert output_type in map(operator.itemgetter(0), output_types.DETAILS), "Unknown output type"
        try:
            o = ExpectedActionOutput.objects.get(action=self, output_type=output_type)
        except ExpectedActionOutput.DoesNotExist:
            o = ExpectedActionOutput(action=self, output_type=output_type)
        o.location = location
        o.save()

    def as_form_data(self):
        output = {
                'id': self.id,
                'name': self.name,
                'project': self.project.id,
                'username': self.username,
                'command': self.command,
                'host': self.host,
                'authorized_keys_entry': self.authorized_keys_entry,
                'index': self.index,
                }
        for output_type, output_full_name in output_types.DETAILS:
            if output_type in output_types.IMPLICIT:
                continue
            try:
                o = ExpectedActionOutput.objects.get(output_type=output_type, action=self)
                output['output_' + output_type] = o.location
            except ExpectedActionOutput.DoesNotExist:
                output['output_' + output_type] = ''
        #for hook_type in self.valid_hooks:
            #if hook_type in self.hooks:
                #output['hook_' + hook_type] = self.hooks[hook_type]
            #else:
                #output['hook_' + hook_type] = ''
        #del output['hooks']
        return output

    def values_without_keys(self):
        data = dict(self.values)
        for k in ['public_key', 'private_key', 'response']:
            if k in data:
                del data[k]
        return data


class ActionResult(models.Model):
    """
    When an Action is run, an ActionResult is created.

    This stores the start time, and when the action finishes, stores the end time
    and status code (0 implies success).

    Any output generated by an action is stored in ActionOutput instances which
    link to this class.
    """
    job = models.ForeignKey('job.Job')

    action = models.ForeignKey('Action')

    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True)

    status_code = models.IntegerField(null=True)

    message = models.TextField(blank=True)

    objects = ManagerWithFirstQuery()

    def __unicode__(self):
        return "%s" % self.action.name

    def save(self):
        super(ActionResult, self).save()

    @property
    def success(self):
        return self.status_code == 0

    @property
    def in_progress(self):
        return self.started_at and self.finished_at is None and self.status_code is None

    @property
    def has_output(self):
        return self.actionoutput_set.count() > 0

    @property
    def stdout(self):
        return self.get_output(output_types.STDOUT)

    @property
    def stderr(self):
        return self.get_output(output_types.STDERR)

    @property
    def duration(self):
        if self.in_progress:
            return None
        return self.finished_at - self.started_at

    def get_output(self, output_type):
        try:
            return self.actionoutput_set.get(output_type=output_type)
        except ActionOutput.DoesNotExist:
            pass
