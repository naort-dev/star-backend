from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from .models import Notification
from utilities.admin_utils import ReadOnlyModelAdmin

class NotificationAdmin(ReadOnlyModelAdmin):
    list_display = ('user', 'title', 'body', 'send_notification',)


admin.site.register(Notification, NotificationAdmin)
