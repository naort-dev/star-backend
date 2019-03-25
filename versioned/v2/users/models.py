from django.db import models
from django.db.models.signals import pre_delete, pre_save
from django.dispatch.dispatcher import receiver
from django.core.exceptions import PermissionDenied


class CelebrityDisplay(models.Model):
    celebrity = models.ForeignKey('users.StargramzUser', related_name='celebrity_display', blank=False, on_delete=models.CASCADE)


@receiver(pre_delete, sender=CelebrityDisplay)
def delete_data(*args, **kwargs):
    raise PermissionDenied


@receiver(pre_save, sender=CelebrityDisplay)
def save_data(instance, **kwargs):
    if not instance.id:
        if CelebrityDisplay.objects.all().count() >= 9:
            raise PermissionDenied
