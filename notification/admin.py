from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from .models import Notification, GroupAdminNotification
from utilities.admin_utils import ReadOnlyModelAdmin

class NotificationAdmin(ReadOnlyModelAdmin):
    list_display = ('user', 'title', 'body', 'send_notification',)


class GroupAdminNotificationAdmin(ReadOnlyModelAdmin):
    list_display = ('user', 'group_name', 'content',)


admin.site.register(Notification, NotificationAdmin)
admin.site.register(GroupAdminNotification, GroupAdminNotificationAdmin)
