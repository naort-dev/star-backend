from django.utils.translation import ugettext_lazy as _
from django.contrib import admin
from .models import New
from utilities.admin_utils import ReadOnlyModelAdmin

class NewsAdmin(ReadOnlyModelAdmin):
    list_display = ('id', 'title', 'description', 'image')

    fieldsets = (
        (_('News Details'), {'fields': ('title', 'description', 'image')}),
    )
    search_fields = ('name',)
    readonly_fields = ('created_date',)

admin.site.register(New, NewsAdmin)

