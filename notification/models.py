from django.db import models
from users.models import StargramzUser, GroupType


class Notification(models.Model):
    user = models.ForeignKey(StargramzUser, related_name='notifcation_user')
    title = models.CharField(max_length=150)
    body = models.CharField(max_length=150)
    send_notification = models.BooleanField(default=False)

    def __str__(self):
        return self.title


class GroupAdminNotification(models.Model):
    user = models.ForeignKey(StargramzUser, related_name='group_requested_user')
    group_name = models.CharField(max_length=150, blank=True, null=True)
    content = models.TextField('contents', max_length=300, blank=True, null=True)
    created_date = models.DateTimeField('Created Date', auto_now_add=True)
    modified_date = models.DateTimeField('Modified Date', auto_now=True)
