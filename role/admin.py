from django.contrib import admin

from role.models import Feature, Role, RoleFeatureMapping


class FeatureAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'code')


class RoleAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'code')


class RoleFeatureMappingAdmin(admin.ModelAdmin):
    list_display = ('id', 'role', 'feature', 'privilege_enabled')
    search_fields = ('role__name', 'role__code', 'feature__code', 'feature__name')

admin.site.register(Feature, FeatureAdmin)
admin.site.register(Role, RoleAdmin)
admin.site.register(RoleFeatureMapping, RoleFeatureMappingAdmin)
