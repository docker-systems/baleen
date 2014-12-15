from StringIO import StringIO

from django.test import TestCase
from django.contrib.auth.models import User

from mock import Mock, patch

from baleen.project.models import Project
from baleen.action.actions import Action, RemoteSSHAction, ExpectedActionOutput
from baleen.artifact.models import output_types


class BaseActionTest(TestCase):

    def setUp(self):
        self.project = Project(name='TestProject')
        self.project.save()
        self.action = RemoteSSHAction(project=self.project, index=0, name='TestAction',
                username='foo', command='echo "blah"')

        self.user = User.objects.create_user('bob', 'bob@bob.com', 'bob')
        self.user.save()
        self.client.login(username='bob', password='bob')

class ActionTest(BaseActionTest):

    def test_statsd_name(self):
        self.assertEqual(self.action.statsd_name, 'testaction')
        self.action.name = 'test*(&#$*&*(@$#'
        self.assertEqual(self.action.statsd_name, 'test')
        self.action.name = 'test something    now'
        self.assertEqual(self.action.statsd_name, 'test_something_now')


class RemoteSSHActionTest(BaseActionTest):

    def setUp(self):
        super(RemoteSSHActionTest, self).setUp()
        self.ea = ExpectedActionOutput(action=self.action, output_type=output_types.XUNIT,
                location='righthere')

        self.ea2 = ExpectedActionOutput(action=self.action, output_type=output_types.COVERAGE_HTML,
                location='rightnow')

    def test_authorized_keys_entry(self):
        keys = self.action.authorized_keys_entry
        self.assertTrue('no-agent-forwarding' in keys)

        self.action.set_output(ExpectedActionOutput(self.action, output_types.XUNIT, 'here'))
        keys = self.action.authorized_keys_entry
        self.assertEqual(keys.split('\n')[0], '# TestAction')


    @patch('paramiko.SSHClient')
    @patch('paramiko.SFTPClient')
    @patch('baleen.action.actions.RemoteSSHAction.fetch_output')
    @patch('baleen.action.actions.RemoteSSHAction._run_command')
    def test_execute(self, run_mock, fetch_mock, sftp_mock, ssh_mock):
        stdout = StringIO()
        stderr = StringIO()

        self.action.execute(stdout, stderr, None)

        ExpectedActionOutput(action=self.action, output_type=output_types.XUNIT, location='xunit.xml')

        self.action.execute(stdout, stderr, None)

    def test_run_command(self):
        stdout = StringIO()
        stderr = StringIO()
        m = Mock()
        chan = Mock()

        m.open_session.return_value = chan
        chan.exit_status_ready.side_effect = [False, False, True]
        chan.recv.side_effect = ['blah', 'blah']
        chan.recv_ready.side_effect = [True, True, False]
        chan.recv_stderr.side_effect = ['argh', 'argh', 'argh']
        chan.recv_stderr_ready.side_effect = [True, True, True, False]

        self.action._run_command('test', m, stdout, stderr)

        self.assertEqual(stdout.getvalue(), 'blah'*2)
        self.assertEqual(stderr.getvalue(), 'argh'*3)

    @patch('baleen.action.actions.make_tarfile')
    @patch('baleen.action.actions.mkdir_p')
    @patch('baleen.action.actions.S_ISDIR')
    def test_fetch(self, ISDIR, mkdir_p, make_tarfile):
        m = Mock()
        m.normalize.return_value = 'robots'
        self.assertEqual(self.action.fetch_output(self.ea, m), None)

        ISDIR.return_value = True
        self.assertEqual(self.action.fetch_output(self.ea, m), None)
        ISDIR.return_value = False
        m.open.return_value.read.return_value = 'test'
        self.assertEqual(self.action.fetch_output(self.ea, m), 'test')

        m.listdir.return_value = []
        ISDIR.return_value = True
        self.assertTrue('rightnow' in self.action.fetch_output(self.ea2, m))
        self.assertTrue(mkdir_p.call_args[0][0] in make_tarfile.call_args[0][0])

        m.stat.return_value = None
        self.assertEqual(self.action.fetch_output(self.ea, m), None)
        self.assertTrue(mkdir_p.call_args[0][0] in make_tarfile.call_args[0][0])

    @patch('baleen.action.actions.S_ISDIR')
    @patch('os.mkdir')
    def test_copy_dir(self, mkdir, ISDIR):
        m = Mock()
        m.listdir.return_value = ['file1', 'file2']
        ISDIR.return_value = False
        self.action._copy_dir(m, 'a', 'b')
        self.assertTrue(m.get.called)
