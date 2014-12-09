from baleen.action.models import Action
from baleen.action.forms import RemoteSSHActionForm as ActionForm

import json

from django.shortcuts import get_object_or_404, redirect, render_to_response
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, HttpResponse

from jsonify.decorators import ajax_request

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
    action = action.get_real_instance()
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
