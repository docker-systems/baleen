from django.contrib import admin

from baleen.project.models import Project, ActionResult, Credential
from baleen.artifact.models import ActionOutput


class CredentialAdmin(admin.ModelAdmin):
    model = Credential
admin.site.register(Credential, CredentialAdmin)

class ProjectAdmin(admin.ModelAdmin):
    model = Project
admin.site.register(Project, ProjectAdmin)


class ActionOutputInline(admin.TabularInline):
    model = ActionOutput


class ActionResultAdmin(admin.ModelAdmin):
    inlines = [ActionOutputInline]
admin.site.register(ActionResult, ActionResultAdmin)
