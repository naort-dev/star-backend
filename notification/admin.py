from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from .models import Notification, GroupAdminNotification
from utilities.admin_utils import ReadOnlyModelAdmin
import json
from django.utils.safestring import mark_safe


class NotificationAdmin(ReadOnlyModelAdmin):
    list_display = ('user', 'title', 'body', 'send_notification',)


class GroupAdminNotificationAdmin(ReadOnlyModelAdmin):
    list_display = ('user', 'group_name',)
    readonly_fields = ('extra_contents', )

    fields = ('user', 'group_name', 'extra_contents')

    def extra_contents(self, instance):
        data = json.loads(instance.content)
        string = ''
        for attribute, value in sorted(data.items()):
            try:
                for attributes, values in value.items():
                    string += "<tr><td>%s - %s</td><td>%s</td></tr>" % (
                        attribute.capitalize(),
                        attributes.capitalize(),
                        str(values)
                    )
            except Exception:
                if value:
                    string += "<tr><td>%s</td><td>%s</td></tr>" % (attribute.capitalize(), str(value))

        return mark_safe("<table width='500px'>%s</table>" % string)


admin.site.register(Notification, NotificationAdmin)
admin.site.register(GroupAdminNotification, GroupAdminNotificationAdmin)
