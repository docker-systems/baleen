import os

from django.db import models
from django.conf import settings

import xml.etree.ElementTree as ET

from jsonfield import JSONField

from baleen.utils import ManagerWithFirstQuery


class output_types(object):
    # TODO: make this pluggable so people can register output types
    XUNIT = 'UX'
    COVERAGE_XML = 'CX'
    COVERAGE_HTML = 'CH'

    STDOUT = 'SO'
    STDIN = 'SI'
    STDERR = 'SE'
    # These types are implicitly an outcome of actions
    IMPLICIT = [ STDOUT, STDIN, STDERR ]

    DETAILS = (
        (XUNIT, 'Xunit'),
        (COVERAGE_XML, 'Coverage XML details'),
        (COVERAGE_HTML, 'Coverage HTML report'),
        (STDOUT, 'stdout'),
        (STDIN, 'stdin'),
        (STDERR, 'stderr'),
    )


class OutputManager(ManagerWithFirstQuery):

    def __init__(self, output_type):
        self.output_type = output_type
        return super(OutputManager, self).__init__()

    def get_query_set(self):
        return super(OutputManager, self).get_query_set().filter(output_type=self.output_type)


class ActionOutput(models.Model):
    """
    An ActionOutput is a generic model for representing output that is the
    result of an action.

    We define seperate a seperate proxy class for each output type, which can
    be used for specific control of doing things with the `output` and
    `data` fields (e.g. parsing xml stored in the output and putting a summary
    in the)
    """
    action_result = models.ForeignKey('project.ActionResult')
    
    output_type = models.CharField(max_length=2,
            choices=output_types.DETAILS,
            default=output_types.STDOUT)

    output = models.TextField(null=True, blank=True)
    data = JSONField()

    objects = ManagerWithFirstQuery()

    def __unicode__(self):
        return "Output %s for Action '%s'" % (
                self.get_output_type_display(),
                self.action_result.action )


class XUnitOutput(ActionOutput):
    objects = OutputManager(output_types.XUNIT)

    def save(self):
        self.output_type=output_types.XUNIT
        super(XUnitOutput, self).save()

    def parse_test_results(self):
        root = ET.fromstring(self.output.encode('utf-8'))
        total_tests = int(root.attrib['tests'])
        errors = int(root.attrib['errors'])
        failures = int(root.attrib['failures'])
        return ((total_tests - errors - failures), total_tests)

    def parse_xunit_failures(self):
        root = ET.fromstring(self.output.encode('utf-8'))
        result = {}
        for test in root.iter('testcase'):
            for failure in test.findall('failure'):
                class_name = test.attrib['classname']
                test_name = test.attrib['name']
                result.setdefault(class_name, {})
                result[class_name][test_name] = {
                        'message': failure.attrib['message'],
                        'details': failure.text,
                        'type': failure.attrib['type'],
                        }
        return result 

    class Meta:
        proxy = True


class CoverageXMLOutput(ActionOutput):
    objects = OutputManager(output_types.COVERAGE_XML)

    def save(self):
        self.output_type=output_types.COVERAGE_XML
        super(CoverageXMLOutput, self).save()

    def parse_coverage_percent(self):
        root = ET.fromstring(self.output.encode('utf-8'))
        return float(root.attrib['line-rate']) * 100

    class Meta:
        proxy = True


class CoverageHTMLOutput(ActionOutput):
    objects = OutputManager(output_types.COVERAGE_HTML)

    def save(self):
        self.output_type=output_types.COVERAGE_HTML
        super(CoverageHTMLOutput, self).save()

    def get_coverage_html_dir(self):
        return os.path.join(settings.ARTIFACT_DIR, self.output)

    class Meta:
        proxy = True
