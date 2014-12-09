from django.conf.urls import patterns, url

urlpatterns = patterns('',
    url(r'^(?P<project_id>\d+)/action$', 'baleen.action.views.add_action', name='add_action'),
    url(r'^(?P<project_id>\d+)/action/(?P<action_id>\d+)$',
        'baleen.action.views.edit_action', name='edit_action'),
    url(r'^(?P<project_id>\d+)/action-order$',
        'baleen.action.views.set_action_order', name='set_action_order'),
)

