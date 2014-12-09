import json
from StringIO import StringIO

from django.test import TestCase
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

from mock import Mock, patch

from baleen.project.models import Project
from baleen.action.models import Action, RemoteSSHAction
from baleen.artifact.models import output_types, ExpectedActionOutput


class BaseActionTest(TestCase):

    def setUp(self):
        self.project = Project(name='TestProject')
        self.project.generate_github_token()
        self.project.save()
        self.action = RemoteSSHAction(project=self.project, index=0, name='TestAction',
                username='foo', command='echo "blah"')
        self.action.save()

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


class ActionViewTest(BaseActionTest):

    def test_add_action(self):
        response = self.client.post(reverse('add_action', kwargs=dict(project_id=self.project.id)),
                content_type='application/json',
                data=json.dumps({'test':'test'}))

        self.assertFalse(json.loads(response.content)['form_saved'])
        self.assertEqual(Action.objects.count(), 1)

        response = self.client.post(reverse('add_action', kwargs=dict(project_id=self.project.id)),
                content_type='application/json',
                data=json.dumps({
                    "username": 'bob',
                    "index": 0, "host": 'localhost', "command": 'ls', "name": 'ls the dir'
                    }))
        self.assertTrue(json.loads(response.content)['form_saved'])
        self.assertEqual(Action.objects.count(), 2)
        return [a.id for a in Action.objects.all()]

    def test_edit_action(self):
        response = self.client.post(reverse('edit_action',
            kwargs=dict(project_id=self.project.id, action_id=self.action.id)),
                content_type='application/json',
                data=json.dumps({'test':'test'}))

        self.assertFalse(json.loads(response.content)['form_saved'])
        self.assertEqual(Action.objects.count(), 1)

        response = self.client.post(reverse('edit_action',
            kwargs=dict(project_id=self.project.id, action_id=self.action.id)),
                content_type='application/json',
                data=json.dumps({
                    "username": 'bob',
                    "index": 0,
                    "host": 'localhost',
                    "command": 'ls',
                    "name": 'ls the dir'
                    }))
        self.assertTrue(json.loads(response.content)['form_saved'])
        self.assertEqual(Action.objects.get(id=self.action.id).command, 'ls')
        self.assertEqual(Action.objects.count(), 1)

    def test_delete_action(self):
        response = self.client.delete(reverse('edit_action',
            kwargs=dict(project_id=self.project.id, action_id=self.action.id)))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Action.objects.count(), 0)

    def test_action_order(self):
        action_ids = self.test_add_action()
        action_ids.reverse()
        data = {'order': action_ids}
        response = self.client.post(reverse('set_action_order',
                    kwargs=dict(project_id=self.project.id)),
                content_type='application/json',
                data=json.dumps(data))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Action.objects.get(id=action_ids[0]).index, 0)
        self.assertEqual(Action.objects.get(id=action_ids[1]).index, 1)

        action_ids.reverse()
        data = {'order': action_ids}
        response = self.client.post(reverse('set_action_order',
                    kwargs=dict(project_id=self.project.id)),
                content_type='application/json',
                data=json.dumps(data))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Action.objects.get(id=action_ids[0]).index, 0)
        self.assertEqual(Action.objects.get(id=action_ids[1]).index, 1)


class RemoteSSHActionTest(BaseActionTest):

    def setUp(self):
        super(RemoteSSHActionTest, self).setUp()
        self.ea = ExpectedActionOutput(action=self.action, output_type=output_types.XUNIT,
                location='righthere')
        self.ea.save()

        self.ea2 = ExpectedActionOutput(action=self.action, output_type=output_types.COVERAGE_HTML,
                location='rightnow')
        self.ea2.save()

    def test_authorized_keys_entry(self):
        keys = self.action.authorized_keys_entry
        self.assertTrue('no-agent-forwarding' in keys)

        self.action.set_output(output_types.XUNIT, 'here')
        keys = self.action.authorized_keys_entry
        self.assertTrue('here' in keys)

    @patch('paramiko.SSHClient')
    @patch('paramiko.SFTPClient')
    @patch('baleen.action.models.RemoteSSHAction.fetch_output')
    @patch('baleen.action.models.RemoteSSHAction._run_command')
    def test_execute(self, run_mock, fetch_mock, sftp_mock, ssh_mock):
        stdout = StringIO()
        stderr = StringIO()

        self.action.execute(stdout, stderr, None)

        expected_output = ExpectedActionOutput(action=self.action, output_type=output_types.XUNIT, location='xunit.xml')
        expected_output.save()

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

    @patch('baleen.action.models.make_tarfile')
    @patch('baleen.action.models.mkdir_p')
    @patch('baleen.action.models.S_ISDIR')
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

    @patch('baleen.action.models.S_ISDIR')
    @patch('os.mkdir')
    def test_copy_dir(self, mkdir, ISDIR):
        m = Mock()
        m.listdir.return_value = ['file1', 'file2']
        ISDIR.return_value = False
        self.action._copy_dir(m, 'a', 'b')
        self.assertTrue(m.get.called)
