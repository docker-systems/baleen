from django import template
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from django.core.urlresolvers import reverse
from xml.etree.ElementTree import ParseError

from baleen.artifact.models import XUnitOutput, output_types, CoverageXMLOutput, CoverageHTMLOutput
from baleen.job.models import Job

register = template.Library()

@register.inclusion_tag('job/show_coverage.html')
def render_coverage(c_xml, c_html):
    """
    Take an action result, and if it has an associated coverage xml/html output
    the coverage percentage and a link.

    If ar is a list, then it will take the first item.
    
    TODO split up handling lists and individual entries
    """
    if not c_xml:
        return {}

    from baleen.project.models import ActionResult
    if not isinstance(c_xml, ActionResult):
        c_xml = c_xml[0]
    if c_html and not isinstance(c_html, ActionResult):
        c_html = c_html[0]
    j = c_xml.job

    if c_xml.job.started_at:
        previous_job = Job.objects.filter(finished_at__lte=j.started_at).first()

    coverage_xml = None
    coverage_html = None
    url = None
    previous_job = None
    previous_coverage_xml = None

    try:
        coverage_xml = CoverageXMLOutput.objects.get(action_result=c_xml)
        coverage_html = CoverageHTMLOutput.objects.get(action_result=c_html)
    except (CoverageHTMLOutput.DoesNotExist, CoverageXMLOutput.DoesNotExist):
        pass

    if coverage_html and coverage_html.get_coverage_html_dir():
        url = reverse(
                'baleen.job.views.view_specific_action_html_coverage',
                kwargs=dict(
                    project_id=j.project.id,
                    job_id=j.id,
                    filename='index.html',
                    action=slugify(coverage_html.action_result.action))
                )

    cover_exists = coverage_xml or coverage_html
    if cover_exists and previous_job:
        # TODO this action result should be checked it's from the same action
        previous_action_result = previous_job.get_action_result_with_output(output_types.COVERAGE_XML)
        if previous_action_result:
            previous_coverage_xml = CoverageXMLOutput.objects.get(action_result=previous_action_result)

    return {
            'coverage_html_url': url,
            'coverage_percent': coverage_xml.parse_coverage_percent() if coverage_xml else None,
            'previous_coverage_percent': previous_coverage_xml.parse_coverage_percent() if previous_coverage_xml else None,
            }

@register.inclusion_tag('job/xunit_summary.html')
def render_xunit_summary(ar):
    """
    Take an action result, and if it has an associated xunit output, render
    successes / total.

    If ar is a list, then it will aggregate the the successes across all
    action results with an associated xunit output.

    TODO split up handling lists and individual entries
    """
    from baleen.project.models import ActionResult
    # handle a single action_result, or aggregate across action results
    if isinstance(ar, ActionResult):
        action_results = [ar]
    else:
        action_results = ar
    try:
        xunit_outputs = XUnitOutput.objects.filter(action_result__in=action_results)
        if len(xunit_outputs) == 0:
            success = None
            total = None
        else:
            success = 0
            total = 0

        for xo in xunit_outputs:
            s, t= xo.parse_test_results()
            success += s
            total += t
    except (ParseError, TypeError):
        success = '?'
        total = '?'
    return { 'success': success, 'total': total }

@register.inclusion_tag('job/xunit_failures.html')
def render_xunit_failures(action_result):
    failures = []
    try:
        xunit_outputs = XUnitOutput.objects.filter(action_result=action_result)
        for xo in xunit_outputs:
            dict_failures = xo.parse_xunit_failures()
            for cls, tests in dict_failures.items():
                for test_name, details in tests.items():
                    failures.append((cls, test_name, details['message'], details['details']))
    except (XUnitOutput.DoesNotExist, ParseError, TypeError):
        pass
    return { 'failure': failures }

@register.filter()
def render_commits(job):
    commits = job.github_data.get('commits', [])
    if len(commits) == 1:
        return commits[0].get('message','')[:75]
    else:
        return "%d commits" % len(commits)

@register.filter()
def render_trigger(job):
    if job.manual_by:
        return 'manual deploy'
    elif job.github_data and not job.manual_by:
        return job.github_compare_url()

@register.filter()
def job_status_badge(job):
    preamble = '<a href="%s">' % reverse('view_job', kwargs=dict(project_id=job.project.id, job_id=job.id))
    if not job.started_at:
        badge_span = '<span class="label">pending</span>'
    elif not job.finished_at:
        badge_span = '<span class="label">in progress</span></a>'
    elif job.success:
        badge_span = '<span class="label label-success">success</span></a>'
    elif job.rejected:
        badge_span = '<span class="label">rejected</span></a>'
    else:
        badge_span = '<span class="label label-important">failure</span></a>'
    return mark_safe(preamble + badge_span)
