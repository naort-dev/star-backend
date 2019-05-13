from django.db import models
from django.conf import settings
from django.dispatch import receiver
from django.db.models.signals import post_save
from utilities.utils import upload_image_s3
from config.models import Config
import os


class CelebrityDisplayOrganizer(models.Model):
    title = models.CharField(max_length=120, null=True, blank=True)
    profession = models.ForeignKey('users.Profession', related_name='profession_celebrity', null=True, blank=True, on_delete=models.CASCADE)
    featured = models.BooleanField(default=False)

    def __str__(self):
        if self.profession and self.profession.title:
            return self.profession.title
        elif self.title:
            return self.title
        else:
            return "Display organizer"


class CelebrityDisplay(models.Model):
    celebrity = models.ForeignKey('users.StargramzUser', related_name='celebrity_display', blank=True, null=True, on_delete=models.CASCADE)
    order = models.IntegerField('celebrity order', blank=True, null=True)
    celebrity_display = models.ForeignKey(CelebrityDisplayOrganizer, related_name='celebrity_display_organizer', null=True,
                                          blank=True, on_delete=models.CASCADE)


def upload_function(obj, file_name):
    return '%shome_page_videos/%s' % (settings.MEDIA_ROOT, file_name)


class HomePageVideo(models.Model):
    video = models.FileField(upload_to=upload_function, verbose_name='Video')
    created_date = models.DateTimeField('Created Date', auto_now_add=True)
    modified_date = models.DateTimeField('Modified Date', auto_now=True)


@receiver(post_save, sender=HomePageVideo)
def uploading_function(sender, instance, **kwargs):
    name = instance.video.name.split("/")[-1]
    s3folder = Config.objects.get(key='home_page_videos').value
    upload_image_s3(instance.video.name, s3folder+name)
    os.remove(instance.video.name)
