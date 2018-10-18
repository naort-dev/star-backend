# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2018-10-18 06:05
from __future__ import unicode_literals

from django.db import migrations
from job.tasks import check_file_exist_in_s3
from django.conf import settings
from utilities.utils import get_pre_signed_get_url, upload_image_s3
import urllib.request


def migration_update_s3_video_thumbnail(apps, schema_editor):
    """
    Migrating starsona video thumbnails to public folder
    :param apps:
    :param schema_editor:
    :return:
    """
    videos = apps.get_model('stargramz', 'StargramVideo')
    video_thumb = "videos/stargram_videos/"
    video_thumb_new = "videos/starsona_thumb/"
    your_media_root = settings.MEDIA_ROOT + 'thumbnails/'
    for video in videos.objects.all():
        try:
            if check_file_exist_in_s3(video_thumb + video.thumbnail) is not False:
                img_url = get_pre_signed_get_url(video.thumbnail, video_thumb)
                image_original = your_media_root + video.thumbnail
                urllib.request.urlretrieve(img_url, image_original)
                try:
                    # Upload the thumbnail image to s3
                    upload_image_s3(image_original, video_thumb_new+video.thumbnail)
                except Exception as e:
                    print('Upload failed with reason %s', str(e))

        except Exception as e:
            print(str(e))


class Migration(migrations.Migration):

    dependencies = [
        ('stargramz', '0006_bookingadminadd'),
    ]

    operations = [
        migrations.RunPython(migration_update_s3_video_thumbnail)
    ]
