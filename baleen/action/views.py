from baleen.action.models import BuildDefinition
from baleen.action.forms import RemoteSSHActionForm as ActionForm

import json

from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, HttpResponse

from jsonify.decorators import ajax_request


@login_required()
@ajax_request
def add_action(request, project_id):
    # can't edit actions anymore, only builddefinitions
    return HttpResponseBadRequest()


@login_required()
@ajax_request
def edit_action(request, project_id, action_id):
    # can't edit actions anymore, only builddefinitions
    return HttpResponseBadRequest()


@login_required()
@ajax_request
def set_action_order(request, project_id):
    # can't edit actions anymore, only builddefinitions
    return HttpResponseBadRequest()
