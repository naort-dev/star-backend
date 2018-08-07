from django.contrib import admin
from utilities.utils import get_user_role_details


class ReadOnlyTabularInline(admin.TabularInline):
    """
        ModelAdmin class that prevents modifications through the admin.

        The changelist and the detail view work, but a 403 is returned
        if one actually tries to edit an object.
    """
    def has_add_permission(self, request):
        return True if verify_user_role(request) else False

    def get_readonly_fields(self, request, obj=None):
        read_only_fields = tuple([f.name for f in self.model._meta.fields]) + self.readonly_fields
        return self.readonly_fields if verify_user_role(request) else read_only_fields

    def has_delete_permission(self, request, obj=None):
        return True if verify_user_role(request) else False

    def has_change_permission(self, request, obj=None):
        return True if verify_user_role(request) else (request.method in ['GET', 'HEAD'] and
                super().has_change_permission(request, obj))


class ReadOnlyStackedInline(admin.StackedInline):
    """
        ModelAdmin class that prevents modifications through the admin.

        The changelist and the detail view work, but a 403 is returned
        if one actually tries to edit an object.
    """
    def has_add_permission(self, request):
        return True if verify_user_role(request) else False

    def get_readonly_fields(self, request, obj=None):
        read_only_fields = tuple([f.name for f in self.model._meta.fields]) + self.readonly_fields
        return self.readonly_fields if verify_user_role(request) else read_only_fields

    def has_delete_permission(self, request, obj=None):
        return True if verify_user_role(request) else False

    def has_change_permission(self, request, obj=None):
        return True if verify_user_role(request) else (request.method in ['GET', 'HEAD'] and
                super().has_change_permission(request, obj))


class ReadOnlyModelAdmin(admin.ModelAdmin):
    """
    ModelAdmin class that prevents modifications through the admin.

    The changelist and the detail view work, but a 403 is returned
    if one actually tries to edit an object.
    """

    def get_readonly_fields(self, request, obj=None):
        read_only_fields = tuple([f.name for f in self.model._meta.fields]) + self.readonly_fields
        return self.readonly_fields if verify_user_role(request) else read_only_fields

    def has_add_permission(self, request):
        return True if verify_user_role(request) else False

    def has_change_permission(self, request, obj=None):
        return True if verify_user_role(request) else (request.method in ['GET', 'HEAD'] and
                super().has_change_permission(request, obj))

    def has_delete_permission(self, request, obj=None):
        return True if verify_user_role(request) else False

    def change_view(self, request, object_id=None, form_url='', extra_context=None):
        extra_context = extra_context or {}
        if not verify_user_role(request):
            extra_context['show_save_and_continue'] = False
            extra_context['show_save'] = False

        return super().change_view(request, object_id, extra_context=extra_context)


def verify_user_role(request):
    """
    Verify the role of the user and prohibit the user from record changing
    :param request:
    :return: Boolean
    """
    role = get_user_role_details(request.user)
    if 'role_code' in role and (role['role_code'] == 'R1005' or role['role_code'] == 'R1006'):
        return False
    else:
        return True
