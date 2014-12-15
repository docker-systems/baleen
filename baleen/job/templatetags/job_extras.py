from django import template
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from django.core.urlresolvers import reverse
from xml.etree.ElementTree import ParseError

from baleen.artifact.models import XUnitOutput, output_types, CoverageXMLOutput, CoverageHTMLOutput
from baleen.job.models import Job

register = template.Library()

@register.inclusion_tag('job/show_coverage.html')
def render_coverage(ar):
    if not ar:
        return {}
    if ar.job.started_at:
        previous_job = Job.objects.filter(finished_at__lte=ar.job.started_at).first()

    coverage_xml = None
    coverage_html = None
    url = None
    previous_job = None
    previous_coverage_xml = None

    try:
        coverage_xml = CoverageXMLOutput.objects.get(action_result=ar)
        coverage_html = CoverageHTMLOutput.objects.get(action_result=ar)
    except (CoverageHTMLOutput.DoesNotExist, CoverageXMLOutput.DoesNotExist):
        pass

    if coverage_html and coverage_html.get_coverage_html_dir():
        url = reverse(
                'baleen.job.views.view_specific_action_html_coverage',
                kwargs=dict(
                    project_id=ar.job.project.id,
                    job_id=ar.job.id,
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
def render_xunit_summary(action_result):
    try:
        xunit_output = XUnitOutput.objects.get(action_result=action_result)
        success, total = xunit_output.parse_test_results()
    except XUnitOutput.DoesNotExist:
        total = None
        success = None
    except (ParseError, TypeError):
        success = '?'
        total = '?'
    return { 'success': success, 'total': total }

@register.inclusion_tag('job/xunit_failures.html')
def render_xunit_failures(action_result):
    failures = []
    try:
        xunit_output = XUnitOutput.objects.get(action_result=action_result)
        dict_failures = xunit_output.parse_xunit_failures()
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
        val = dict(
                github_data_url=job.github_data.get('compare',''),
                commits=render_commits(job),
                )
        return mark_safe('<a href="{github_data_url}">{commits}</a>'.format(**val))

@register.filter()
def render_initiating_user(job):
    if job.manual_by:
        return job.manual_by
    elif job.github_data:
        return job.github_data.get('pusher',{}).get('name','unknown')
    else:
        return 'unknown'

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
