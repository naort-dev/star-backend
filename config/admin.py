from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from config.models import Config


class ConfigAdmin(admin.ModelAdmin):
    """
        Configurable admin
    """
    list_display = ('id', 'key', 'value', 'status', 'created_date', 'modified_date',)

    fieldsets = (
        (_('Configurable info'), {'fields': ('key', 'value', 'status',)}),
    )
    search_fields = ('key',)

    ordering = ('key', )
    readonly_fields = ('created_date', 'modified_date', )
    list_per_page = 10
    ordering = ['-id', ]

    class Media:
        css = {
            'all': ('admin/css/stargramz.css',),
        }


admin.site.register(Config, ConfigAdmin)
