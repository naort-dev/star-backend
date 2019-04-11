from django.contrib import admin
from .models import CelebrityDisplay
from utilities.admin_utils import ReadOnlyModelAdmin


class CelebrityDisplayAdmin(ReadOnlyModelAdmin):
    list_display = ('id', 'celebrity', 'name')
    ordering = ('id',)
    autocomplete_fields = ['celebrity']

    def name(self, instance):
        return instance.celebrity.get_short_name()


admin.site.register(CelebrityDisplay, CelebrityDisplayAdmin)