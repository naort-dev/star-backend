from django.contrib import admin
from .models import CelebrityDisplay
from utilities.admin_utils import ReadOnlyModelAdmin

class CelebrityDisplayAdmin(ReadOnlyModelAdmin):
    list_display = ('id', 'celebrity', 'email')
    ordering = ('id',)

    def email(self, instance):
        return instance.celebrity.email


admin.site.register(CelebrityDisplay, CelebrityDisplayAdmin)