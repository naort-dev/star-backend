from django.db import models
from utilities.konstants import Konstants, K
from django.db.models.signals import post_save
from django.dispatch import receiver
from users.tasks import report_abuse_notify
from utilities.konstants import ROLES, NOTIFICATION_TYPES
from .constants import *
from django.db.models import F
from django.apps import apps
import datetime


REQUEST_TYPES = Konstants(
    K(personalised_video=1, label='Personalized video shout-out'),
    K(event_announcement=2, label='Event Announcement'),
    K(live_question_answer=3, label='Live Question and Answer')
)

STATUS_TYPES = Konstants(
    K(draft=0, label='Draft'),
    K(approval_pending=1, label='Payment Approved'),
    K(pending=2, label='Pending'),
    K(processing=3, label='Processing'),
    K(video_approval=4, label='Video Approval'),
    K(cancelled=5, label='Cancelled'),
    K(completed=6, label='Completed')
)

VIDEO_STATUS = Konstants(
    K(completed=1, label='Completed'),
    K(approved=2, label='Approved'),
    K(rejected=3, label='Rejected'),
    K(live_question=4, label='Live Question'),
    K(live_answer=5, label='Live Answer'),
)

TYPES = Konstants(
    K(type0=0, label='Type 0'),
    K(type1=1, label='Type 1'),
    K(type2=2, label='Type 2'),
    K(type3=3, label='Type 3'),
    K(type4=4, label='Type 4'),
    K(type5=5, label='Type 5'),
    K(type6=6, label='Type 6'),
    K(type7=7, label='Type 7'),
    K(type8=8, label='Type 8'),
)

REQUEST_TYPES = Konstants(
    K(personalised_video=1, label='Personalized video shout-out'),
    K(event_announcement=2, label='Event Announcement'),
    K(live_question_answer=3, label='Live Question and Answer')
)

FILE_TYPES = Konstants(
    K(image=1, label='Image'),
    K(video=2, label='Video')
)


class OccasionRelationship(models.Model):
    """
        Occasions Relationship model
    """
    title = models.CharField('Title', max_length=256)
    status = models.BooleanField('Status', default=False)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ('through_relation__order', 'title')


class Occasion(models.Model):
    """
        Occasions model
    """
    title = models.CharField('Title', blank=False, max_length=256)
    occasion_image = models.FileField(blank=True, null=True)
    date_required = models.BooleanField('Date mandatory', default=False)
    #relationships = models.ManyToManyField('OccasionRelationship', blank=True)
    relationships = models.ManyToManyField('OccasionRelationship', through='OrderRelationship', blank=True)
    type = models.IntegerField(choices=TYPES.choices(), default=TYPES.type1)
    other_check = models.BooleanField('Other check', default=False)
    request_type = models.IntegerField(choices=REQUEST_TYPES.choices(), default=REQUEST_TYPES.personalised_video)
    # data = models.TextField('Data')
    created_date = models.DateTimeField(
        'Created date',
        auto_now_add=True,
        editable=False
    )
    visibility = models.BooleanField('Public Visibility', default=True)

    def __str__(self):
        return self.title


class OrderRelationship(models.Model):
    relation = models.ForeignKey('OccasionRelationship', related_name='through_relation')
    occasion = models.ForeignKey('Occasion', related_name='through_occasion')
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ('order',)


class Stargramrequest(models.Model):
    booking_title = models.CharField('Booking title', max_length=255, blank=True, null=True)
    occasion = models.ForeignKey('Occasion', related_name='request_occasion', blank=True, null=True)
    fan = models.ForeignKey('users.StargramzUser', related_name='request_fan')
    celebrity = models.ForeignKey('users.StargramzUser', related_name='request_celebrity')
    request_details = models.TextField(name='request_details')
    share_check = models.BooleanField(default=False)
    due_date = models.DateField(auto_now_add=True)
    request_status = models.IntegerField(
        choices=STATUS_TYPES.choices(),
        default=STATUS_TYPES.draft
    )
    public_request = models.BooleanField(default=False)
    priorty = models.BooleanField(default=False)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    from_audio_file = models.CharField(max_length=260, blank=True, null=True)
    to_audio_file = models.CharField(max_length=260, blank=True, null=True)
    comment = models.CharField(max_length=260, blank=True, null=True)
    request_type = models.IntegerField(
        choices=REQUEST_TYPES.choices(),
        default=REQUEST_TYPES.personalised_video
    )
    __original_request_status = None

    def __init__(self, *args, **kwargs):
        super(Stargramrequest, self).__init__(*args, **kwargs)
        self.__original_request_status = self.request_status

    def __str__(self):
        return 'Request No- %s' % str(self.pk)

    def save(self, *args, **kwargs):
        """
            Override the save to check the old value of request_status field
        """
        from job.tasks import send_email_notification
        from notification.tasks import send_notification
        from payments.tasks import create_request_refund
        from stargramz.tasks import notify_fan_reaction_videos_and_feedback
        if self.request_status != self.__original_request_status:
            send_email_notification.apply_async(
                (self.pk,),
                eta=datetime.datetime.utcnow() + datetime.timedelta(seconds=5)
            )
            if self.request_status == STATUS_TYPES.cancelled:
                create_request_refund.delay()
            if self.request_status == STATUS_TYPES.completed:
                model = apps.get_model('users', 'StargramzUser')
                user = model.objects.get(id=self.fan.id)
                user.completed_view_count = F('completed_view_count') + 1
                user.save()
                user.refresh_from_db()

                # Trigger push/email notifications for reactions & reviews
                notify_fan_reaction_videos_and_feedback.apply_async(
                    (self.pk,),
                    eta=datetime.datetime.utcnow() + datetime.timedelta(seconds=25)
                )

                body_content = NOTIFICATION_Q_A % self.celebrity.get_short_name() if self.request_type == 3 else \
                    NOTIFICATION_REQUEST_COMPLETE_BODY

                kw = {'field': 'fan_starsona_videos'}
                data = {'id': self.pk, 'type': NOTIFICATION_TYPES.fan_myvideos_completed_details,
                        'role': ROLES.fan, 'completed_fan_unseen_count': user.completed_view_count}

                send_notification.apply_async((
                    self.fan.id,
                    NOTIFICATION_REQUEST_COMPLETE_TITLE,
                    body_content,
                    data,
                    kw
                ), countdown=10)
        super(Stargramrequest, self).save(*args, **kwargs)
        self.__original_request_status = self.request_status

    class Meta:
        verbose_name = 'Bookings'
        verbose_name_plural = 'Bookings'


@receiver(post_save, sender=Stargramrequest)
def update_remaining_limits(sender, instance, **kwargs):
    from stargramz.tasks import request_limit_notification
    model = apps.get_model('users', 'Celebrity')
    total_requests = Stargramrequest.objects.filter(celebrity_id=instance.celebrity_id,
                                                    request_status__in=[1, 2, 3]
                                                    ).count()
    try:
        celebrity = model.objects.get(user_id=instance.celebrity_id)
        pending_total = int(celebrity.weekly_limits) - int(total_requests)
        if pending_total < 1:
            request_limit_notification(celebrity)
        celebrity.remaining_limit = pending_total if pending_total > 0 else 0
        celebrity.save()
    except Exception as e:
        print(str(e))


class StargramVideo(models.Model):
    stragramz_request = models.ForeignKey('Stargramrequest', related_name='request_video')
    video = models.CharField('Request Video', max_length=600, null=True, blank=True)
    thumbnail = models.CharField('Thumbnail Image', max_length=600, null=True, blank=True)
    duration = models.TimeField('Duration', blank=True, null=True)
    read_status = models.BooleanField(default=False)
    status = models.IntegerField(choices=VIDEO_STATUS.choices(), default=VIDEO_STATUS.completed)
    featured = models.BooleanField(default=False)
    created_date = models.DateTimeField('Created Date', auto_now_add=True)
    modified_date = models.DateTimeField('Modified Date', auto_now=True)
    visibility = models.BooleanField('Public Visibility', default=True)
    width = models.IntegerField('Width', blank=True, null=True)
    height = models.IntegerField('Height', blank=True, null=True)
    comments_count = models.IntegerField('Comments count', blank=True, null=True, default=0)

    def __str__(self):
        return 'Starsona Video - %s' % str(self.pk)

    class Meta:
        verbose_name = 'Videos'
        verbose_name_plural = 'Video'
        ordering = ['-id', '-created_date']


class ReportAbuse(models.Model):
    request = models.ForeignKey('Stargramrequest', related_name='request_abuse')
    comments = models.TextField('Comments')
    reported_by = models.ForeignKey('users.StargramzUser', related_name='reported_user')
    read_flag = models.BooleanField('Verified abuse', default=False)
    created_date = models.DateTimeField('Created Date', auto_now_add=True)

    def __str__(self):
        return 'Abuse reported'


@receiver(post_save, sender=ReportAbuse)
def verify_abuse_reported(sender, instance, **kwargs):
    if kwargs.get('created', False):
        report_abuse_notify.delay(instance.reported_by_id, instance.request_id)


class Comment(models.Model):
    video = models.ForeignKey('StargramVideo', related_name='comment_video')
    comments = models.TextField('Comments')
    user = models.ForeignKey('users.StargramzUser', related_name='commented_user')
    reply = models.ForeignKey('self', blank=True, null=True, related_name='reply_comment')
    created_date = models.DateTimeField('Created Date', auto_now_add=True)

    def __str__(self):
        return 'Comment - %s' % str(self.pk)

    class Meta:
        ordering = ['-created_date']

@receiver(post_save, sender=Comment)
def update_comments_count(sender, instance, **kwargs):
    video_comments_count = Comment.objects.filter(video=instance.video).count()
    try:
        StargramVideo.objects.filter(id=instance.video_id).update(comments_count=video_comments_count)
    except Exception as e:
        pass


class Reaction(models.Model):
    booking = models.ForeignKey('Stargramrequest', related_name='booking_reaction')
    user = models.ForeignKey('users.StargramzUser', related_name='user_reaction')
    file_type = models.IntegerField('File type', choices=FILE_TYPES.choices())
    reaction_file = models.CharField('Reaction File', max_length=600, blank=False)
    file_thumbnail = models.CharField('Thumbnail', max_length=600, null=True, blank=True)
    admin_approval = models.BooleanField('Admin Approved', default=False)
    order = models.IntegerField('list order', blank=True, null=True)
    created_date = models.DateTimeField('Created Date', auto_now_add=True)

    def __str__(self):
        return 'Reaction - %s' % str(self.pk)


class BookingAdminAdd(Stargramrequest):
    """
        Proxy Class of Stargramrequest Model for Admin Adding
    """
    class Meta:
        verbose_name = 'Bookings Admin Adding'
        verbose_name_plural = 'Bookings Admin Adding'
        proxy = True