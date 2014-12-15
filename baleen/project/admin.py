from django.contrib import admin

from baleen.project.models import Project
from baleen.action.models import BuildDefinition

class BuildDefinitionInline(admin.TabularInline):
    model = BuildDefinition

class ProjectAdmin(admin.ModelAdmin):
    inlines = [BuildDefinitionInline]
admin.site.register(Project, ProjectAdmin)
