import os
import tempfile
from stat import S_ISDIR

from django.db import models
from django.conf import settings

import xml.etree.ElementTree as ET

from jsonfield import JSONField

from baleen.utils import ManagerWithFirstQuery, mkdir_p, make_tarfile


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


class ExpectedActionOutput(models.Model):
    action = models.ForeignKey('action.Action')

    output_type = models.CharField(max_length=2, choices=output_types.DETAILS)

    location = models.CharField(max_length=255)

    def __unicode__(self):
        return "Action '%s' expects %s output" % (
                self.action.name,
                self.get_output_type_display(), )

    def _copy_dir(self, sftp, src, dest):
        file_list = sftp.listdir(path=src)
        for f in file_list:
            src_f = os.path.join(src,f)
            dest_f = os.path.join(dest,f)
            if S_ISDIR(sftp.stat(src_f).st_mode):
                os.mkdir(os.path.join(dest,f))
                self._copy_dir(sftp, src_f, dest_f)
            sftp.get(remotepath=src_f, localpath=dest_f)

    def fetch(self, sftp):
        # Assume that default directory is home of the login user
        location = self.location.replace('~', sftp.normalize('.'))

        stat = sftp.stat(location)
        if not stat:
            return None

        if self.output_type == output_types.COVERAGE_HTML:
            assert S_ISDIR(stat.st_mode)
            dest = tempfile.mkdtemp(prefix=os.path.split(location)[-1], dir=settings.HTMLCOV_DIR)
            self._copy_dir(sftp, location, dest)
            # create an archive in LXC's temp directory.
            # Then the baleen webapp LXC uses watchdog to extract the archive to somewhere
            # the webapp can serve them from.

            # make staging dir if it doesn't exist, assumes worker will have permissions
            mkdir_p(settings.HTMLCOV_LXC_STAGING_DIR)
            # make archive
            archive_path = os.path.join(
                    settings.HTMLCOV_LXC_STAGING_DIR,
                    os.path.basename(dest) + ".tar.gz")
            make_tarfile(archive_path, dest)

            return os.path.split(dest)[-1]
        else:
            if S_ISDIR(stat.st_mode):
                return None
            # to copy file from remote to local
            f = sftp.open(location)
            content = f.read()
            f.close()
            return content


class ActionOutput(models.Model):
    """
    An ActionOutput is a generic model for representing output that is the
    result of an action.

    We define seperate a seperate proxy class for each output type, which can
    be used for specific control of doing things with the `output` and
    `data` fields (e.g. parsing xml stored in the output and putting a summary
    in the)
    """
    output_type = models.CharField(max_length=2,
            choices=output_types.DETAILS,
            default=output_types.STDOUT)
    action_result = models.ForeignKey('action.ActionResult')

    output = models.TextField(null=True, blank=True)
    data = JSONField()

    objects = ManagerWithFirstQuery()

    def __unicode__(self):
        return "Output %s for Action '%s'" % (
                self.get_output_type_display(),
                self.action_result.action.name )


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
        return os.path.join(settings.HTMLCOV_DIR, self.output)

    class Meta:
        proxy = True
