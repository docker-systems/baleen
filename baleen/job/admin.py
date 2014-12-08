from django.contrib import admin

from baleen.job.models import Job
from baleen.action.models import ActionResult

class ActionResultInline(admin.ModelAdmin):
    model = ActionResult

class JobAdmin(admin.ModelAdmin):
    #inlines = [ActionResultInline]
    pass
admin.site.register(Job, JobAdmin)
