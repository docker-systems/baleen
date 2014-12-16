from django.conf.urls import patterns, include, url
from django.views.generic import RedirectView, TemplateView

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', 'baleen.views.home', name='home'),
    url(r'^project/', include('baleen.project.urls')),
    #url(r'^project/', include('baleen.action.urls')),
    #url(r'^jobs/', include('baleen.job.urls')),
    url(r'^github/(?P<github_token>[^/]+)$', 'baleen.views.github', name='github_url'),
    #url(r'^users/', include('baleen.project.users')),

    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/', include(admin.site.urls)),

    # Account related urls
    (r'^accounts/', include('allauth.urls')),
    #(r'^accounts/profile/$', RedirectView.as_view(url='/')),

)
