from StringIO import StringIO

from django.test import TestCase
from django.contrib.auth.models import User

from mock import Mock, patch

from baleen.action.ssh import RemoteSSHAction

from baleen.action import (
        ExpectedActionOutput,
        parse_build_definition,
        ActionPlan,
        DockerActionPlan
        )

from baleen.project.models import Project, BuildDefinition
from baleen.artifact.models import output_types

class ActionPlanTest(TestCase):

    def setUp(self):
        self.project = Project(name='TestProject')
        self.project.save()
        self.action = RemoteSSHAction(project=self.project, index=0, name='TestAction',
                username='foo', command='echo "blah"')

        the_plan = ''
        self.bd = BuildDefinition(project=self.project, plan_type='docker',
                raw_plan=the_plan)
        self.bd.save()

    def test_parse_build_definition(self):
        action_steps = parse_build_definition(self.bd)
        self.assertEqual(action_steps, [], 'no action steps for blank plan')

    def test_iterate_steps(self):
        ap = ActionPlan(self.bd)
        ap.plan = [1, 2, 3]
        self.assertEqual([ap for step in ap], [1, 2, 3])


class DockerActionPlanTest(TestCase):

    def setUp(self):
        self.project = Project(name='TestProject')
        self.project.save()
        self.action = RemoteSSHAction(project=self.project, index=0, name='TestAction',
                username='foo', command='echo "blah"')

    def create_plan(self, the_plan):
        self.bd = BuildDefinition(project=self.project, plan_type='docker',
                raw_plan=the_plan)
        self.bd.save()

    def user_and_login(self):
        self.user = User.objects.create_user('bob', 'bob@bob.com', 'bob')
        self.user.save()
        self.client.login(username='bob', password='bob')

    def test_formulate_blank_plan(self):
        self.create_plan('')
        ap = DockerActionPlan(self.bd)
        action_steps = ap.formulate_plan()
        self.assertEqual(action_steps, [], 'no action steps for blank plan')

    def test_formulate_plan(self):
        self.create_plan("""
depends:
    docker.example.com/db: git@github.com/docker-systems/example-db.git

build:
    docker.example.com/blah: .
"""
        )
        ap = DockerActionPlan(self.bd)
        action_steps = ap.formulate_plan()
        self.assertEqual(action_steps, [
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
                ], 'steps to build')



class ExpectedActionOutputTest(TestCase):

    def setUp(self):
        self.project = Project(name='TestProject')
        self.project.save()
        self.action = RemoteSSHAction(project=self.project, index=0, name='TestAction',
                username='foo', command='echo "blah"')

    def test_unicode(self):
        ea = ExpectedActionOutput(self.action, 'CH')
        self.assertEqual(unicode(ea), "Action 'TestAction' expects Coverage HTML report output")

    def test_output_type_display(self):
        ea = ExpectedActionOutput(self.action, 'CH')
        self.assertEqual(ea.get_output_type_display(), "Coverage HTML report")


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
    @patch('gearman.GearmanClient')
    @patch('baleen.action.ssh.RemoteSSHAction.fetch_output')
    @patch('baleen.action.ssh.RemoteSSHAction._run_command')
    def test_execute(self, run_mock, fetch_mock, gearman_mock, sftp_mock, ssh_mock):
        stdout = StringIO()
        stderr = StringIO()
        run_mock.return_value = {'code': 0}

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

    @patch('baleen.action.ssh.make_tarfile')
    @patch('baleen.action.ssh.mkdir_p')
    @patch('baleen.action.ssh.S_ISDIR')
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

    @patch('baleen.action.ssh.S_ISDIR')
    @patch('os.mkdir')
    def test_copy_dir(self, mkdir, ISDIR):
        m = Mock()
        m.listdir.return_value = ['file1', 'file2']
        ISDIR.return_value = False
        self.action._copy_dir(m, 'a', 'b')
        self.assertTrue(m.get.called)
