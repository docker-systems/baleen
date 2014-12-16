import os

from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404, render_to_response, render, get_list_or_404, redirect
from django.http import HttpResponseBadRequest, HttpResponse, Http404
from django.template import RequestContext

from jsonify.decorators import ajax_request
from sendfile import sendfile

import json

from baleen.project.models import ActionResult
from baleen.job.models import Job
from baleen.artifact.models import CoverageHTMLOutput


@login_required()
def view_job(request, project_id, job_id):
    job = get_object_or_404(Job, id=job_id)
    context = {
        'project': job.project,
        'job': job,
        'github_data': job.github_data if job.github_data else {}
    }
    context_instance=RequestContext(request)
    return render_to_response('project/view_job.html', context, context_instance)

@login_required()
def mark_job_done(request, project_id, job_id):
    """ Used to kill a job that's stuck """
    job = get_object_or_404(Job, id=job_id)
    job.kill()
    return redirect(reverse('show_project', kwargs=dict(project_id=project_id)))

@login_required()
def view_specific_action_html_coverage(request, project_id, job_id, action, filename):
    """
    Serve htmlcov directory for a specific action.
    """
    action_result = get_object_or_404(ActionResult, action_slug=action, job_id=job_id)
    cov_output = CoverageHTMLOutput.objects.filter(action_result=action_result).first()

    if cov_output is None:
        raise Http404

    path = cov_output.get_coverage_html_dir()

    return sendfile(request, os.path.join(path, filename))

@login_required()
def view_html_coverage(request, project_id, job_id, filename):
    """
    Scan the matching Job for an ActionResult that contains htmlcov, then redirect
    to the specific url for that ActionResult.

    Just used for convenience as most projects will probably not serve up multiple
    coverage reports.
    """
    job = get_object_or_404(Job, id=job_id)
    cov_output = CoverageHTMLOutput.objects.filter(action_result__in=job.actionresult_set.all()).first()

    if cov_output is None:
        raise Http404
    else:
        return redirect(reverse('view_specific_action_html_coverage', kwargs=dict(
            project_id=project_id,
            job_id=job_id,
            action=cov_output.action_result.action_slug,
            filename=filename,)
            ))
