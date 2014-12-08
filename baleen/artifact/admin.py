from django.contrib import admin

from baleen.artifact.models import ActionOutput, ExpectedActionOutput


class ExpectedActionOutputAdmin(admin.ModelAdmin):
    pass
admin.site.register(ExpectedActionOutput, ExpectedActionOutputAdmin)


class ActionOutputAdmin(admin.ModelAdmin):
    pass
admin.site.register(ActionOutput, ActionOutputAdmin)
