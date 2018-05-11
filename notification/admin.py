from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from .models import Notification


class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'body', 'send_notification',)


admin.site.register(Notification, NotificationAdmin)
