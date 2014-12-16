import json

from django.test import TestCase

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

from baleen.project.models import Project
from baleen.action.ssh import RemoteSSHAction

from mock import patch


class ProjectTest(TestCase):

    def setUp(self):
        self.project = Project(name='TestProject')
        self.project.save()
        self.action = RemoteSSHAction(project=self.project, index=0, name='TestAction',
                username='foo', command='echo "blah"')

        self.user = User.objects.create_user('bob', 'bob@bob.com', 'bob')
        self.user.save()
        self.client.login(username='bob', password='bob')

    def test_statsd_name(self):
        self.assertEqual(self.project.statsd_name, 'testproject')
        self.project.name = 'test*(&#$*&*(@$#'
        self.assertEqual(self.project.statsd_name, 'test')
        self.project.name = 'test something    now'
        self.assertEqual(self.project.statsd_name, 'test_something_now')

    @patch('gearman.GearmanClient')
    def test_github_hook(self, gearman):
        data = {'payload': json.dumps({'commits': []})}
        response = self.client.post(reverse('github_url', kwargs={'github_token': self.project.github_token}), data=data)
        self.assertContains(response, 'processed')


class ProjectTestView(TestCase):

    def setUp(self):
        self.project = Project(name='TestProject')
        self.project.save()
        self.action = RemoteSSHAction(project=self.project, index=0, name='TestAction',
                username='foo', command='echo "blah"')

        self.user = User.objects.create_user('bob', 'bob@bob.com', 'bob')
        self.user.save()
        self.client.login(username='bob', password='bob')

    def test_index(self):
        response = self.client.get(reverse('project_index'))
        self.assertContains(response, "TestProject")

    @patch('gearman.GearmanClient')
    def test_add(self, gearman):
        response = self.client.get(reverse('add_project'))

        post_data = {
                'name':	'A Great Project',
                'site_url': 'http://google.com',
                'submit': 'Add Project'
                }
        response = self.client.post(reverse('add_project'), data=post_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Project.objects.count(), 2)

    def test_show(self):
        response = self.client.get(reverse('show_project', kwargs=dict(project_id=self.project.id)))
        self.assertContains(response, "TestProject")

    @patch('gearman.GearmanClient')
    def test_update(self, gearman):
        post_data = {
                'name':	'A Great Project',
                'site_url': 'http://google.com',
                'op': 'save'
                }
        response = self.client.post(reverse('show_project', kwargs=dict(project_id=self.project.id)),
                data=post_data
                )

        self.assertContains(response, "A Great Project")

    def test_delete(self):
        post_data = {
                'name':	'A Great Project',
                'site_url': 'http://google.com',
                'op': 'delete'
                }
        response = self.client.post(reverse('show_project', kwargs=dict(project_id=self.project.id)),
                data=post_data
                )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Project.objects.count(), 0)

    @patch('baleen.job.models.manual_run')
    def test_manual_deploy(self, mrun):
        response = self.client.get(reverse('manual_deploy', kwargs=dict(project_id=self.project.id)))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(mrun.called)
