from django.contrib import admin

from baleen.project.models import Project
from baleen.action.models import Action

class ActionInline(admin.TabularInline):
    model = Action

class ProjectAdmin(admin.ModelAdmin):
    inlines = [ActionInline]
admin.site.register(Project, ProjectAdmin)

