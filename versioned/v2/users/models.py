from django.db import models
from django.conf import settings
from django.dispatch import receiver
from django.db.models.signals import post_save
from utilities.utils import upload_image_s3
from config.models import Config
import os
from utilities.konstants import Konstants, K
from django.core.validators import MaxValueValidator, MinValueValidator
from users.constants import MAX_RATING_VALUE, MIN_RATING_VALUE


VIDEO_TYPES = Konstants(
    K(fan_video=1, label='Fan Video'),
    K(star_video=2, label='Star Video')
)


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
    video_type = models.IntegerField('Video Type', choices=VIDEO_TYPES.choices(), default=VIDEO_TYPES.star_video)


@receiver(post_save, sender=HomePageVideo)
def uploading_function(sender, instance, **kwargs):
    name = instance.video.name.split("/")[-1]
    s3folder = Config.objects.get(key='home_page_videos').value
    upload_image_s3(instance.video.name, s3folder+name)
    os.remove(instance.video.name)


class CelebrityDashboard(models.Model):
    user = models.ForeignKey('users.StargramzUser', related_name='celebrity', on_delete=models.CASCADE)
    total_earnings = models.DecimalField('Total Earnings', max_digits=10, decimal_places=2, blank=True)
    pending_payments = models.DecimalField('Pending Payments', max_digits=10, decimal_places=2, blank=True)
    total_video_count = models.IntegerField('Total Video Count', default=0, blank=True)
    total_comment_count = models.IntegerField('Total Comment Count', default=0, blank=True)
    total_reaction_video_count = models.IntegerField('Total Reaction Video Count', default=0, blank=True)
    rating = models.DecimalField('Celebrity rating', max_digits=4, decimal_places=2, blank=True, default=0.00,
                                 validators=[MinValueValidator(MIN_RATING_VALUE),
                                             MaxValueValidator(MAX_RATING_VALUE)])
    open_booking_count = models.IntegerField('Open Booking Count', default=0, blank=True)
    recent_comment_count = models.IntegerField('Recent Comment Count', default=0, blank=True)
    recent_reaction_video_count = models.IntegerField('Recent Reaction Video Count', default=0, blank=True)
    recent_rating_count = models.IntegerField('Recent Rating Count', default=0, blank=True)
    recent_tip_count = models.IntegerField('Recent Tip Count', default=0, blank=True)
    recent_tip_amount = models.DecimalField('Recent Tip Amount', max_digits=10, decimal_places=2, blank=True)
    recent_deposit_amount = models.DecimalField('Recent Deposit Amount', max_digits=7, decimal_places=2, blank=True)
    recent_deposit_date = models.DateTimeField('Recent Deposit Date', default=None, blank=True, null=True)
    profile_share_count = models.IntegerField('Profile Share Count', default=0, blank=True)
    last_profile_shared_at = models.DateTimeField('Last Profile Shared Date', default=None, blank=True, null=True)
    video_share_count = models.IntegerField('Video Share Count', default=0, blank=True)
    last_video_shared_at = models.DateTimeField('Last Video Shared Date', default=None, blank=True, null=True)
    thirty_days_booking_count = models.IntegerField('30 Days Booking Count', default=0, blank=True)
    one_twenty_days_booking_count = models.IntegerField('120 Days Booking Count', default=0, blank=True)
    one_eighty_days_booking_count = models.IntegerField('180 Days Booking Count', default=0, blank=True)
    has_biography = models.BooleanField('Check Biography', default=False)
    has_referral = models.BooleanField('Check Referral', default=False)
