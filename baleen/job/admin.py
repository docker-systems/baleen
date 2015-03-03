from django.contrib import admin

from baleen.job.models import Job
from baleen.project.models import ActionResult

class ActionResultInline(admin.ModelAdmin):
    model = ActionResult

class JobAdmin(admin.ModelAdmin):
    date_hierarchy = 'started_at'
    list_display = ('id', 'project', 'started_at', 'success')
admin.site.register(Job, JobAdmin)
