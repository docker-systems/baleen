from django.contrib import admin

from baleen.action.models import ActionResult, BuildDefinition
from baleen.artifact.models import ActionOutput


class BuildDefinitionAdmin(admin.ModelAdmin):
    pass
admin.site.register(BuildDefinition, BuildDefinitionAdmin)


class ActionOutputInline(admin.TabularInline):
    model = ActionOutput


class ActionResultAdmin(admin.ModelAdmin):
    inlines = [ActionOutputInline]
admin.site.register(ActionResult, ActionResultAdmin)
