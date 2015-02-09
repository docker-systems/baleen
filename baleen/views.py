import json

from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, Http404

from baleen.project.models import Project
from baleen.job.models import Job


def home(request):
    return redirect(reverse('project_index'))


@csrf_exempt
def github(request, github_token):
    if request.method != 'POST':
        raise Http404

    project = get_object_or_404(Project, github_token=github_token)

    # catch the ping
    if request.META.get('HTTP_X_GITHUB_EVENT', 'push') == 'ping':
        project.github_data_received = True
        project.save()
        return HttpResponse('processed')

    github_data = json.loads(request.body)

    # Only let pushes to the branch we care about through...
    if project.branch:
        if not 'ref' in github_data:
            return HttpResponse('processed')
        if github_data['ref'] != "refs/heads/%s" % project.branch:
            return HttpResponse('processed')

    # Temporary cleanup - remove key containing data we can't store and don't
    # care about anyway
    for c in github_data['commits']:
        if 'tmp' in c:
            del c['tmp']

    # Mark the project as having received data
    project.github_data_received = True
    project.save()

    # Submit the job!
    job = Job(project=project, github_data=github_data)
    job.save()
    job.submit()

    return HttpResponse('processed')
