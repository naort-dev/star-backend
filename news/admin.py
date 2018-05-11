from django.utils.translation import ugettext_lazy as _
from django.contrib import admin
from .models import New

class NewsAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'description', 'image')

    fieldsets = (
        (_('News Details'), {'fields': ('title', 'description', 'image')}),
    )
    search_fields = ('name',)
    readonly_fields = ('created_date',)

admin.site.register(New, NewsAdmin)

