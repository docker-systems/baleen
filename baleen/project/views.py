import datetime
import random
import string

from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404, redirect, render_to_response
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.utils.timezone import make_aware, get_default_timezone

from crispy_forms.layout import Submit

import baleen.project.models as m
from baleen.utils import get_credential_key_pair
from baleen.project.forms import ProjectForm
from baleen.artifact.models import output_types


def flash(request, msg):
    from django.contrib import messages
    messages.add_message(request, messages.INFO, msg)


@login_required()
def index(request):
    projects = m.Project.objects.all()
    min_date_aware = make_aware(datetime.datetime.min, get_default_timezone())
    def get_last_job_time(x):
        j = x.last_job()
        return j.received_at if j else min_date_aware
    projects = sorted(projects, key=get_last_job_time, reverse=True)

    context_instance=RequestContext(request)
    return render_to_response('project/index.html',
            {
                'projects': projects,
            },
            context_instance)


@login_required()
def add(request):
    temp_name = request.session.get('add_project_temporary_credential_name', None)
    if request.method == 'POST' and temp_name:
        form = ProjectForm(request.POST)

        privkey, pubkey = get_credential_key_pair(name=temp_name, user=request.user)
        if form.is_valid():
            project = form.save(commit=False)
            project.creator = request.user
            project.public_key = pubkey
            project.private_key = privkey
            project.save()
            flash(request, 'Project added OK')

            # Attach keys to project, remove user
            privkey.project = project
            privkey.user = None
            privkey.name = 'deploykey_' + project.name + '_private'
            privkey.save()

            pubkey.project = project
            pubkey.user = None
            pubkey.name = 'deploykey_' + project.name + '_public'
            pubkey.save()

            return redirect(reverse('show_project', kwargs={'project_id': project.id}))
    else:
        if request.method == 'POST':
            flash(request, 'There was missing information in your session, please try again')
        if temp_name:
            privkey, pubkey = get_credential_key_pair(name=temp_name, user=request.user)
        else:
            N = 32
            temp_name = ''.join(random.choice(
                string.ascii_uppercase + string.digits) for _ in range(N)
                )
            # Don't do anything with private key
            _, pubkey = get_credential_key_pair(name=temp_name, user=request.user)
            request.session['add_project_temporary_credential_name'] = temp_name

        form = ProjectForm()

    context_instance=RequestContext(request)
    form.helper.add_input(Submit('submit', 'Add Project'))
    #form.helper.add_input(Text('submit', 'Add Project'))
    form.helper.form_action = 'add_project'
    context = { 'form': form, 'deploy_key': pubkey.value}

    return render_to_response('project/add.jinja2', context, context_instance)


@login_required()
def show(request, project_id):
    p = get_object_or_404(m.Project, id=project_id)
    if request.method == 'POST':
        project, form = update(request, p)
        if project is None:
            return redirect(reverse('project_index'))
    else:
        form = ProjectForm(instance=p)

    action_data = [x for x in p.action_plan()]
    
    context_instance = RequestContext(request)

    #form.helper.form_action = reverse('show_project')
    form.helper.add_input(Submit('op', 'Save'))
    form.helper.add_input(Submit('op', 'Delete'))

    jobs = p.job_set.order_by('-received_at')[:20]
    jobs_with_test_results = []
    for j in jobs:
        jobs_with_test_results.append((
            j,
            j.get_action_result_with_output(output_types.XUNIT),
            j.get_action_result_with_output(output_types.COVERAGE_XML),
            j.get_action_result_with_output(output_types.COVERAGE_HTML)
            ))

    current_job = p.current_job()
    if current_job:
        cj = current_job
        current_job = (
                cj,
                cj.get_action_result_with_output(output_types.XUNIT),
                cj.get_action_result_with_output(output_types.COVERAGE_XML),
                cj.get_action_result_with_output(output_types.COVERAGE_HTML)
                )

    context = {
        'jobs': jobs_with_test_results,
        'current_job': current_job,
        'action_data': action_data,
        'form': form,
        'project': p,
        }
    return render_to_response('project/show.jinja2', context, context_instance)


def update(request, project):
    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        op = request.POST['op']
        if op.lower() == 'save':
            if form.is_valid():
                project = form.save()
                flash(request, 'Project updated OK')
        if op.lower() == 'delete':
            project.delete()
            flash(request, 'Project deleted OK')
            return None, form
    return project, form


@login_required()
def manual_deploy(request, project_id):
    from baleen.job.models import manual_run
    project = get_object_or_404(m.Project, id=project_id)
    manual_run(project, request.user)
    return redirect(reverse('show_project', kwargs=dict(project_id=project.id)))
