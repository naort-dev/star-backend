from django.utils.translation import ugettext_lazy as _
from django.contrib import admin
from .models import Promocode


class PromocodeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'code', 'discount')

    fieldsets = (
        (_('Basic info'), {'fields': ('name', 'code')}),
        (_('Coupon info'), {'fields': ('specific_user', 'promo_users', 'users_per_coupon',
                                       'type', 'discount', 'uses_per_coupon')}),
        (_('Status info'), {'fields': ('status',)}),
        (_('Important dates'), {'fields': ('valide_from', 'valide_to', 'created_date', 'modified_date')})
    )
    search_fields = ('name', 'code', )
    readonly_fields = ('created_date', 'modified_date',)

admin.site.register(Promocode, PromocodeAdmin)
