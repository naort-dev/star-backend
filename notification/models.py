from django.db import models
from users.models import StargramzUser


class Notification(models.Model):
    user = models.ForeignKey(StargramzUser, related_name='notifcation_user')
    title = models.CharField(max_length=150)
    body = models.CharField(max_length=150)
    send_notification = models.BooleanField(default=False)

    def __str__(self):
        return self.title
