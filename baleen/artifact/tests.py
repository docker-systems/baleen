from django.test import TestCase

from baleen.artifact.models import (
        XUnitOutput, output_types, ActionOutput,
        CoverageXMLOutput
        )
from baleen.project.models import Project
from baleen.action.ssh import RemoteSSHAction
from baleen.action import ExpectedActionOutput
from baleen.job.models import Job

from mock import Mock, patch


class TestActionOutput(TestCase):

    def setUp(self):
        self.project = Project(name='TestProject')
        self.project.save()

        self.action = RemoteSSHAction(project=self.project, index=0, name='TestAction',
                username='foo', command='echo "blah"')

        self.job = Job(project=self.project, github_data='{}')
        self.job.save()

        self.job.record_action_start(self.action)
        response = {
                'stdout': 'just some output yo',
                'code': 0,
                }
        self.result = self.job.record_action_response(self.action, response)
        self.result.save()

        self.action_output = ActionOutput.objects.get(action_result=self.result,
                output_type=output_types.STDOUT)

    def test_unicode(self):
        self.assertEqual(unicode(self.action_output), u"Output stdout for Action 'RemoteSSHAction: TestAction'")

    def test_in_progress(self):
        self.assertEqual(self.result.in_progress, False)

    def test_has_output(self):
        self.assertEqual(self.result.has_output, True)

    def test_stdout(self):
        self.assertEqual(self.result.stdout.output, 'just some output yo')

    def test_stderr(self):
        self.assertEqual(self.result.stderr.output, '')


class TestCoverageXMLOutput(TestCase):

    def setUp(self):
        self.project = Project(name='TestProject')
        self.project.save()

        self.action = RemoteSSHAction(project=self.project, index=0, name='TestAction',
                username='foo', command='echo "blah"')

        self.job = Job(project=self.project, github_data='{}')
        self.job.save()

        ea = ExpectedActionOutput(action=self.action, output_type=output_types.COVERAGE_XML)

        self.job.record_action_start(self.action)
        cover_xml = """<?xml version="1.0" encoding="UTF-8"?>
<cover line-rate="0.97"></cover>"""
        response = {
                'output': {'CX': cover_xml},
                'code': 0,
                }
        self.result = self.job.record_action_response(self.action, response)
        self.result.save()
        self.cover_xml_result = CoverageXMLOutput.objects.get(action_result__id=self.result.id)

    def test_parse_coverage(self):
        line_rate = self.cover_xml_result.parse_coverage_percent()
        self.assertEqual(line_rate, 97)


class TestXUnitOutput(TestCase):

    def setUp(self):
        self.project = Project(name='TestProject')
        self.project.save()

        self.action = RemoteSSHAction(project=self.project, index=0, name='TestAction',
                username='foo', command='echo "blah"')

        self.job = Job(project=self.project, github_data='{}')
        self.job.save()

        ea = ExpectedActionOutput(action=self.action, output_type=output_types.XUNIT)

        self.job.record_action_start(self.action)
        xunit_xml = """<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="nosetests" tests="4" errors="0" failures="1" skip="0">
    <testcase classname="tests.PermissionsTest" name="test_see_blocks" time="0.597" />
    <testcase classname="tests.DashboardTest" name="test_get" time="0.337" />
    <testcase classname="tests.UserPermissionsTest" name="test_admin_can_see_all" time="0.270">
        <failure message="the end" type="error">Waga</failure>
    </testcase>
    <testcase classname="tests.models" name="check_model_for_changes" time="0.001" />
</testsuite>"""
        response = {
                'output': {'UX': xunit_xml},
                'code': 0,
                }
        self.result = self.job.record_action_response(self.action, response)
        self.result.save()
        self.xunit_result = XUnitOutput.objects.get(action_result__id=self.result.id)

    def test_get_xunit_failures(self):
        self.assertTrue('tests.UserPermissionsTest' in self.xunit_result.parse_xunit_failures())

    def test_parse_test_results(self):
        success, total = self.xunit_result.parse_test_results()
        self.assertEqual(success, 3)
        self.assertEqual(total, 4)


class TestExpectedOutput(TestCase):

    def setUp(self):
        self.project = Project(name='TestProject')
        self.project.save()

        self.action = RemoteSSHAction(project=self.project, index=0, name='TestAction',
                username='foo', command='echo "blah"')

        self.ea = ExpectedActionOutput(action=self.action, output_type=output_types.XUNIT,
                location='righthere')

        self.ea2 = ExpectedActionOutput(action=self.action, output_type=output_types.COVERAGE_HTML,
                location='rightnow')

    def test_unicode(self):
        self.assertEqual(unicode(self.ea), u"Action 'TestAction' expects Xunit output")
