from django.contrib import admin

from baleen.artifact.models import ActionOutput


class ActionOutputAdmin(admin.ModelAdmin):
    pass
admin.site.register(ActionOutput, ActionOutputAdmin)
