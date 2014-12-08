import reversion

from django.contrib import admin

from baleen.action.models import Action, ActionResult
from baleen.artifact.models import ActionOutput, ExpectedActionOutput


class ExpectedActionOutputInline(admin.TabularInline):
    model = ExpectedActionOutput


class ActionAdmin(reversion.VersionAdmin):
    inlines = [ExpectedActionOutputInline]
admin.site.register(Action, ActionAdmin)


class ActionOutputInline(admin.TabularInline):
    model = ActionOutput


class ActionResultAdmin(admin.ModelAdmin):
    inlines = [ActionOutputInline]
admin.site.register(ActionResult, ActionResultAdmin)

