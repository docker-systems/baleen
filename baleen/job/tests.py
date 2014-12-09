from django.test import TestCase
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.utils.timezone import now

from baleen.project.models import Project
from baleen.job.models import Job, manual_run
from baleen.action.models import RemoteSSHAction, ActionResult
from baleen.artifact.models import (
        output_types, ActionOutput,
        ExpectedActionOutput
        )

from mock import patch, Mock

class JobTest(TestCase):

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

        self.job = Job(project=self.project, github_data={})
        self.job.save()

    def test_unicode(self):
        self.assertTrue('Job' in unicode(self.job))

    @patch('gearman.GearmanClient')
    def test_submit(self, m):
        c = Mock()
        m.return_value = c
        self.job.submit()
        self.assertTrue(c.submit_job.called)

    @patch('gearman.GearmanClient')
    def test_manual_run(self, m):
        c = Mock()
        m.return_value = c

        job = manual_run(self.project, self.user)

        job.submit()
        self.assertTrue(c.submit_job.called)

    @patch('gearman.GearmanClient')
    def test_manual_no_prior_job(self, m):
        c = Mock()
        m.return_value = c
        self.job.delete()

        job = manual_run(self.project, self.user)

        job.submit()
        self.assertTrue(c.submit_job.called)

    def test_record_start(self):
        self.job.record_start(231)
        self.assertEqual(self.job.actionresult_set.count(), 0)

    def test_reject(self):
        self.job.reject()
        self.assertTrue(self.job.rejected)

    @patch('os.kill')
    def test_kill_job(self, m):
        self.job.record_start(231)
        self.job.kill()
        self.assertTrue(m.called)

    def test_record_action_start(self):
        self.job.record_action_start(self.action)

        result = ActionResult.objects.get(job=self.job, action=self.action)
        self.assertEqual(result.finished_at, None)
        self.assertEqual(result.status_code, None)
        self.assertEqual(result.job, self.job)

    def test_record_action_response(self):
        result = self.job.record_action_start(self.action)

        response = {
                'stdout': 'blah',
                'code': 0,
                }
        result = self.job.record_action_response(self.action, response)
        self.assertTrue(result.finished_at)
        self.assertTrue(result.success)

        result.delete()

        result = self.job.record_action_start(self.action)
        response = {
                'stdout': 'blah',
                'code': 1,
                }
        result = self.job.record_action_response(self.action, response)

        self.assertFalse(result.success)

    def test_get_filenames(self):
        result = self.job.get_live_job_filenames()
        self.assertTrue('stdout' in result[0])
        self.assertTrue('stderr' in result[1])

    def test_get_action_result_with_output(self):
        self.job.record_action_start(self.action)
        response = {
                'stdout': 'blah',
                'code': 0,
                }
        result = self.job.record_action_response(self.action, response)
        ao = ActionOutput(output='<xml></xml>', action_result=result, output_type=output_types.XUNIT)
        ao.save()


        self.assertEqual(self.job.get_action_result_with_output(output_types.XUNIT), result)
        self.assertEqual(self.job.get_action_result_with_output(output_types.COVERAGE_HTML), None)

    def test_view_job(self):
        url = reverse('view_job', kwargs=dict(project_id=self.project.id, job_id=self.job.id))
        response = self.client.get(url)
        self.assertContains(response, 'TestProject')

    def test_mark_done(self):
        url = reverse('mark_job_done', kwargs=dict(project_id=self.project.id, job_id=self.job.id))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

        self.assertEqual(self.job.success, False)

    def test_view_html_coverage(self):
        ea2 = ExpectedActionOutput(action=self.action, output_type=output_types.COVERAGE_HTML,
                location='rightnow')
        ea2.save()

        self.job.record_action_start(self.action)
        response = {
                'output': {'CH': 'test'},
                'code': 0,
                }
        self.result = self.job.record_action_response(self.action, response)
        self.result.save()

        url = reverse('view_html_coverage', kwargs=dict(project_id=self.project.id,
            job_id=self.job.id,
            filename='test'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    @patch('baleen.job.views.sendfile')
    def test_view_specific_html_coverage(self, m):
        from django.http import HttpResponse
        m.return_value = HttpResponse('test')
        ea2 = ExpectedActionOutput(action=self.action, output_type=output_types.COVERAGE_HTML,
                location='rightnow')
        ea2.save()

        self.job.record_action_start(self.action)
        response = {
                'output': {'CH': 'test'},
                'code': 0,
                }
        self.result = self.job.record_action_response(self.action, response)
        self.result.save()

        url = reverse('view_html_coverage', kwargs=dict(project_id=self.project.id,
            job_id=self.job.id,
            filename='test'))
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(m.called)


from baleen.job.templatetags.job_extras import (job_status_badge,
        render_initiating_user, render_trigger, render_commits,
        render_xunit_summary, render_coverage)

class JobTemplateTagsTest(TestCase):

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

        self.job = Job(project=self.project, github_data={})
        self.job.save()

    def test_status_badge(self):
        self.assertTrue('pending' in job_status_badge(self.job))
        self.job.started_at = now()
        self.job.save()
        self.assertTrue('in progress' in job_status_badge(self.job))
        self.job.finished_at = now()
        self.job.success = True
        self.job.save()
        self.assertTrue('success' in job_status_badge(self.job))
        self.job.success = False
        self.job.rejected = True
        self.job.save()
        self.assertTrue('rejected' in job_status_badge(self.job))
        self.job.rejected = False
        self.job.save()
        self.assertTrue('failure' in job_status_badge(self.job))

    def test_render_initiating_user(self):
        self.assertEqual(render_initiating_user(self.job), 'unknown')
        self.job.manual_by = self.user
        self.job.save()
        self.assertEqual(render_initiating_user(self.job).username, 'bob')
        self.job.manual_by = None
        self.job.github_data = { 'pusher': {'name': 'mary'} }
        self.job.save()
        self.assertEqual(render_initiating_user(self.job), 'mary')

    def test_render_trigger(self):
        self.assertEqual(render_trigger(self.job), None)
        self.job.manual_by = self.user
        self.job.save()
        self.assertEqual(render_trigger(self.job), 'manual deploy')
        self.job.manual_by = None
        self.job.github_data = {
                'compare': 'testurl',
                'commits': [ {'message' : 'zoom1'}, ]
                }
        self.job.save()
        self.assertTrue('testurl' in render_trigger(self.job))

    def test_render_commits(self):
        self.assertEqual(render_commits(self.job), '0 commits')
        self.job.github_data = { 'commits': [
            {'message' : 'zoom1'}, 
            ] }
        self.job.save()
        self.assertEqual(render_commits(self.job), 'zoom1')
        self.job.github_data = { 'commits': [
            {'message' : 'zoom1'}, 
            {'message' : 'zoom2'}, 
            ] }
        self.job.save()
        self.assertEqual(render_commits(self.job), '2 commits')

    def test_render_xunit_summary(self):
        self.assertEqual(render_xunit_summary(self.job.test_action_result()),
                {'total': None,'success': None})

    def test_render_coverage(self):
        ea = ExpectedActionOutput(action=self.action, output_type=output_types.COVERAGE_XML)
        ea.save()
        ea2 = ExpectedActionOutput(action=self.action, output_type=output_types.XUNIT)
        ea2.save()

        self.job.record_action_start(self.action)
        cover_xml = """<?xml version="1.0" encoding="UTF-8"?>
<cover line-rate="0.97"></cover>"""
        response = {
                'output': {'CX': cover_xml, 'UX': ''},
                'code': 0,
                }
        self.result = self.job.record_action_response(self.action, response)
        self.result.save()
        ctxt = render_coverage(self.job.test_action_result())
        self.assertEqual(97.0, ctxt['coverage_percent'])

    def test_render_coverage_with_html(self):
        ea = ExpectedActionOutput(action=self.action, output_type=output_types.COVERAGE_XML)
        ea.save()
        ea2 = ExpectedActionOutput(action=self.action, output_type=output_types.COVERAGE_HTML,
                location='rightnow')
        ea2.save()
        ea3 = ExpectedActionOutput(action=self.action, output_type=output_types.XUNIT)
        ea3.save()

        self.job.record_action_start(self.action)
        cover_xml = """<?xml version="1.0" encoding="UTF-8"?>
<cover line-rate="0.97"></cover>"""
        response = {
                'output': {'CX': cover_xml, 'CH': 'blah', 'UX': ''},
                'code': 0,
                }
        self.result = self.job.record_action_response(self.action, response)
        self.result.save()
        ctxt = render_coverage(self.job.test_action_result())
        self.assertTrue('index.html' in ctxt['coverage_html_url'])
