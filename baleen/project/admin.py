from django.contrib import admin

from baleen.project.models import Project, ActionResult, BuildDefinition, Credential
from baleen.artifact.models import ActionOutput


class BuildDefinitionInline(admin.TabularInline):
    model = BuildDefinition


class CredentialAdmin(admin.ModelAdmin):
    model = Credential
admin.site.register(Credential, CredentialAdmin)

class ProjectAdmin(admin.ModelAdmin):
    inlines = [BuildDefinitionInline]
admin.site.register(Project, ProjectAdmin)


class BuildDefinitionAdmin(admin.ModelAdmin):
    pass
admin.site.register(BuildDefinition, BuildDefinitionAdmin)


class ActionOutputInline(admin.TabularInline):
    model = ActionOutput


class ActionResultAdmin(admin.ModelAdmin):
    inlines = [ActionOutputInline]
admin.site.register(ActionResult, ActionResultAdmin)
