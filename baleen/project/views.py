import baleen.project.models as m
from baleen.action.models import Action
from baleen.project.forms import ProjectForm, ActionForm

import datetime
import json

from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404, redirect, render_to_response
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.http import HttpResponseBadRequest, HttpResponse

from django.utils.timezone import make_aware, get_default_timezone

from crispy_forms.layout import Submit

from jsonify.decorators import ajax_request


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
    return render_to_response('project/index.html', {'projects': projects}, context_instance)


@login_required()
def add(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save()
            flash(request, 'Project added OK')
            return redirect(reverse('show_project', kwargs={'project_id': project.id}))
    else:
        form = ProjectForm()

    context_instance=RequestContext(request)
    form.helper.add_input(Submit('submit', 'Add Project'))
    form.helper.form_action = 'add_project'
    context = { 'form': form }

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

    action_data = []
    for i, action in enumerate(p.ordered_actions):
        action_data.append(action.as_form_data())

    context_instance = RequestContext(request)

    #form.helper.form_action = reverse('show_project')
    form.helper.add_input(Submit('op', 'Save'))
    form.helper.add_input(Submit('op', 'Delete'))

    context = {
        'jobs': p.job_set.order_by('-received_at')[:20],
        'current_job': p.current_job(),
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


@login_required()
@ajax_request
def add_action(request, project_id):
    if request.method in ['PUT', 'POST']:
        data = json.loads(request.body)
        data['project'] = project_id
        form = ActionForm(data)
        if form.is_valid():
            action = form.save()
            # Return JSON response if form was OK
            response_data = {'form_saved': True, 'data': action.as_form_data()}
        else:
            # Send what were errors
            response_data = {'form_saved': False, 'errors': form.errors}
        return HttpResponse(json.dumps(response_data), content_type="application/json")


@login_required()
@ajax_request
def edit_action(request, project_id, action_id):
    # Change this to use action index
    if request.method in ['GET']:
        return HttpResponseBadRequest()
    action = get_object_or_404(Action, id=action_id)
    if request.method in ['PUT', 'POST']:
        data = json.loads(request.body)
        data['project'] = project_id
        form = ActionForm(data, instance=action)
        if form.is_valid():
            action = form.save()
            # Return JSON response if form was OK
            response_data = {'form_saved': True, 'data': action.as_form_data()}
        else:
            # Send what were errors
            response_data = {'form_saved': False, 'errors': form.errors}
        return HttpResponse(json.dumps(response_data), content_type="application/json")
    if request.method == 'DELETE':
        action.delete()
        return {}


@login_required()
@ajax_request
def set_action_order(request, project_id):
    if request.method == 'POST':
        data = json.loads(request.body)
        counter = 0
        for action_id in data['order']:
            a = Action.objects.get(id=action_id, project__id=project_id)
            a.index = counter
            a.save()
            counter += 1
    return {}
