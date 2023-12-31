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
import pytz
from .utils import average_response_time_calculator
from django.contrib.contenttypes.fields import GenericRelation
from django.utils import timezone


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
    K(completed=6, label='Completed'),
    K(reprocessing=7, label='Reprocessing'),
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
    template_type = models.IntegerField(choices=TYPES.choices(), default=TYPES.type1)

    def __str__(self):
        return self.title


class OrderRelationship(models.Model):
    relation = models.ForeignKey('OccasionRelationship', related_name='through_relation', on_delete=models.CASCADE)
    occasion = models.ForeignKey('Occasion', related_name='through_occasion', on_delete=models.CASCADE)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ('order',)


class Stargramrequest(models.Model):
    booking_title = models.CharField('Booking title', max_length=255, blank=True, null=True)
    occasion = models.ForeignKey('Occasion', related_name='request_occasion', blank=True, null=True, on_delete=models.CASCADE)
    fan = models.ForeignKey('users.StargramzUser', related_name='request_fan', on_delete=models.CASCADE)
    celebrity = models.ForeignKey('users.StargramzUser', related_name='request_celebrity', on_delete=models.CASCADE)
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
    host_audio_file = models.CharField(max_length=260, blank=True, null=True)
    honor_audio_file = models.CharField(max_length=260, blank=True, null=True)
    comment = models.CharField(max_length=260, blank=True, null=True)
    request_type = models.IntegerField(
        choices=REQUEST_TYPES.choices(),
        default=REQUEST_TYPES.personalised_video
    )
    reprocessed = models.BooleanField('Reprocessing', default=False)
    booking_statement = models.CharField('Booking Statement', max_length=500, blank=True, null=True)
    recent_activity_date = models.DateTimeField(blank=True, null=True, default=timezone.now)
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
        booking_id = self.pk
        from job.tasks import send_email_notification, notify_fan_reaction_videos_and_feedback, request_slack_message
        from notification.tasks import send_notification
        from payments.tasks import create_request_refund
        from users.models import Celebrity
        if self.request_status != self.__original_request_status:
            send_email_notification.apply_async(
                (booking_id,),
                eta=datetime.datetime.utcnow() + datetime.timedelta(seconds=5)
            )
            request_slack_message.apply_async(
                (booking_id,),
                eta=datetime.datetime.utcnow() + datetime.timedelta(seconds=5)
            )
            # Reprocessing the request to add video and bypassing payment
            if self.request_status == STATUS_TYPES.reprocessing:
                self.reprocessed = True

            if self.request_status == STATUS_TYPES.cancelled:
                create_request_refund.delay()
            if self.request_status == STATUS_TYPES.pending:
                Celebrity.objects.filter(user_id=self.celebrity.id).update(trending_star_score=F('trending_star_score') + 10)
            if self.request_status == STATUS_TYPES.completed:
                model = apps.get_model('users', 'StargramzUser')
                user = model.objects.get(id=self.fan.id)
                user.completed_view_count = F('completed_view_count') + 1
                user.save()
                user.refresh_from_db()

                # Trigger push/email notifications for reactions & reviews
                later = datetime.datetime.utcnow() + datetime.timedelta(minutes=59)
                notify_fan_reaction_videos_and_feedback.apply_async(args=(booking_id,), eta=later)
                average_response_time_calculator(self.celebrity, self.created_date, self.modified_date)
                # body_content = NOTIFICATION_Q_A % self.celebrity.get_short_name() if self.request_type == 3 else \
                #     NOTIFICATION_REQUEST_COMPLETE_BODY
                #
                # kw = {'field': 'fan_starsona_videos'}
                # data = {'id': self.pk, 'type': NOTIFICATION_TYPES.fan_myvideos_completed_details,
                #         'role': ROLES.fan, 'completed_fan_unseen_count': user.completed_view_count}
                #
                # send_notification.apply_async((
                #     self.fan.id,
                #     NOTIFICATION_REQUEST_COMPLETE_TITLE,
                #     body_content,
                #     data,
                #     kw
                # ), countdown=10)
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


@receiver(post_save, sender=Stargramrequest)
def update_booking_in_dashboard(sender, instance, **kwargs):
    from versioned.v2.users.models import CelebrityDashboard
    from versioned.v2.users.utils import booking_count_update
    try:
        dashboard = CelebrityDashboard.objects.get(user_id=instance.celebrity.id)
        booking_count_update(dashboard)
    except Exception as e:
        print(str(e))
        pass


@receiver(post_save, sender=Stargramrequest)
def create_video_activity(sender, instance, **kwargs):
    from users.models import RecentActivity, ACTIVITY_TYPES

    if instance.request_status == STATUS_TYPES.completed:
        activity = RecentActivity(
            content_object=instance, activity_from_user=instance.celebrity,
            activity_to_user=instance.fan, request=instance,
            activity_type=ACTIVITY_TYPES.video, is_celebrity_activity=True
        )
        activity.save()


class StargramVideo(models.Model):
    stragramz_request = models.ForeignKey('Stargramrequest', related_name='request_video', on_delete=models.CASCADE)
    video = models.CharField('Request Video', max_length=600, null=True, blank=True)
    thumbnail = models.CharField('Thumbnail Image', max_length=600, null=True, blank=True)
    duration = models.TimeField('Duration', blank=True, null=True)
    read_status = models.BooleanField(default=False)
    status = models.IntegerField(choices=VIDEO_STATUS.choices(), default=VIDEO_STATUS.completed)
    featured = models.BooleanField(default=False)
    created_date = models.DateTimeField('Created Date', auto_now_add=True)
    modified_date = models.DateTimeField('Modified Date', auto_now=True)
    visibility = models.BooleanField('Public Visibility', default=True)
    public_visibility = models.BooleanField('New Public Visibility', default=True)
    width = models.IntegerField('Width', blank=True, null=True)
    height = models.IntegerField('Height', blank=True, null=True)
    comments_count = models.IntegerField('Comments count', blank=True, null=True, default=0)
    fan_view_count = models.IntegerField('Fan view count', blank=True, null=True, default=0)
    public_view_count = models.IntegerField('Public view count', blank=True, null=True, default=0)

    def __str__(self):
        return 'Starsona Video - %s' % str(self.pk)

    class Meta:
        verbose_name = 'Videos'
        verbose_name_plural = 'Video'
        ordering = ['-id', '-created_date']


@receiver(post_save, sender=StargramVideo)
def update_video_in_dashboard(sender, instance, **kwargs):
    from versioned.v2.users.models import CelebrityDashboard
    from versioned.v2.users.utils import video_data_update
    try:
        dashboard = CelebrityDashboard.objects.get(user_id=instance.stragramz_request.celebrity.id)
        video_data_update(dashboard)
    except Exception as e:
        print(str(e))
        pass


class ReportAbuse(models.Model):
    request = models.ForeignKey('Stargramrequest', related_name='request_abuse', on_delete=models.CASCADE)
    comments = models.TextField('Comments')
    reported_by = models.ForeignKey('users.StargramzUser', related_name='reported_user', on_delete=models.CASCADE)
    read_flag = models.BooleanField('Verified abuse', default=False)
    created_date = models.DateTimeField('Created Date', auto_now_add=True)

    def __str__(self):
        return 'Abuse reported'


@receiver(post_save, sender=ReportAbuse)
def verify_abuse_reported(sender, instance, **kwargs):
    if kwargs.get('created', False):
        report_abuse_notify.delay(instance.reported_by_id, instance.request_id)


class Comment(models.Model):
    video = models.ForeignKey('StargramVideo', related_name='comment_video', on_delete=models.CASCADE)
    comments = models.TextField('Comments')
    user = models.ForeignKey('users.StargramzUser', related_name='commented_user', on_delete=models.CASCADE)
    reply = models.ForeignKey('self', blank=True, null=True, related_name='reply_comment', on_delete=models.CASCADE)
    created_date = models.DateTimeField('Created Date', auto_now_add=True)
    activities = GenericRelation('users.RecentActivity')

    def __str__(self):
        return 'Comment - %s' % str(self.pk)

    class Meta:
        ordering = ['-created_date']


@receiver(post_save, sender=Comment)
def update_comment_in_dashboard(sender, instance, **kwargs):
    from versioned.v2.users.models import CelebrityDashboard
    from versioned.v2.users.utils import video_data_update
    try:
        dashboard = CelebrityDashboard.objects.get(user_id=instance.video.stragramz_request.celebrity.id)
        video_data_update(dashboard)
    except Exception as e:
        print(str(e))
        pass


@receiver(post_save, sender=Comment)
def update_comments_count(sender, instance, **kwargs):
    video_comments_count = Comment.objects.filter(video=instance.video).count()
    try:
        StargramVideo.objects.filter(id=instance.video_id).update(comments_count=video_comments_count)
    except Exception as e:
        pass


@receiver(post_save, sender=Comment)
def create_comment_activity(sender, instance, **kwargs):
    from users.models import RecentActivity, ACTIVITY_TYPES

    if instance.user == instance.video.stragramz_request.celebrity:
        activity = RecentActivity(
            content_object=instance, activity_from_user=instance.user,
            activity_to_user=instance.video.stragramz_request.fan, request=instance.video.stragramz_request,
            activity_type=ACTIVITY_TYPES.comment, is_celebrity_activity=True
        )
    else:
        activity = RecentActivity(
            content_object=instance, activity_from_user=instance.user,
            activity_to_user=instance.video.stragramz_request.celebrity, request=instance.video.stragramz_request,
            activity_type=ACTIVITY_TYPES.comment, is_celebrity_activity=False
        )
        instance.video.stragramz_request.recent_activity_date = datetime.datetime.now(pytz.UTC)
        instance.video.stragramz_request.save()
    activity.save()


class Reaction(models.Model):
    booking = models.ForeignKey('Stargramrequest', related_name='booking_reaction', on_delete=models.CASCADE)
    user = models.ForeignKey('users.StargramzUser', related_name='user_reaction', on_delete=models.CASCADE)
    file_type = models.IntegerField('File type', choices=FILE_TYPES.choices())
    reaction_file = models.CharField('Reaction File', max_length=600, blank=False)
    file_thumbnail = models.CharField('Thumbnail', max_length=600, null=True, blank=True)
    admin_approval = models.BooleanField('Admin Approved', default=False)
    order = models.IntegerField('list order', blank=True, null=True)
    width = models.IntegerField('Width', blank=True, null=True)
    height = models.IntegerField('Height', blank=True, null=True)
    duration = models.TimeField('Duration', blank=True, null=True)
    created_date = models.DateTimeField('Created Date', auto_now_add=True)
    activities = GenericRelation('users.RecentActivity')

    def __str__(self):
        return 'Reaction - %s' % str(self.pk)

    class Meta:
        verbose_name = 'Reactions'
        verbose_name_plural = 'Reaction'
        ordering = ['-id', '-created_date']


@receiver(post_save, sender=Reaction)
def update_reaction_in_dashboard(sender, instance, **kwargs):
    from versioned.v2.users.models import CelebrityDashboard
    from versioned.v2.users.utils import video_data_update
    try:
        dashboard = CelebrityDashboard.objects.get(user_id=instance.booking.celebrity.id)
        video_data_update(dashboard)
    except Exception as e:
        print(str(e))
        pass


@receiver(post_save, sender=Reaction)
def create_reaction_activity(sender, instance, **kwargs):
    from users.models import RecentActivity, ACTIVITY_TYPES

    if instance.user == instance.booking.celebrity:
        activity = RecentActivity(
            content_object=instance, activity_from_user=instance.user, activity_to_user=instance.booking.fan,
            request=instance.booking, activity_type=ACTIVITY_TYPES.reaction, is_celebrity_activity=True
        )
    else:
        activity = RecentActivity(
            content_object=instance, activity_from_user=instance.user, activity_to_user=instance.booking.celebrity,
            request=instance.booking, activity_type=ACTIVITY_TYPES.reaction, is_celebrity_activity=False
        )
        instance.booking.recent_activity_date = datetime.datetime.now(pytz.UTC)
        instance.booking.save()
    activity.save()


class BookingAdminAdd(Stargramrequest):
    """
        Proxy Class of Stargramrequest Model for Admin Adding
    """
    class Meta:
        verbose_name = 'Bookings Admin Adding'
        verbose_name_plural = 'Bookings Admin Adding'
        proxy = True


class ReactionAbuse(models.Model):
    reaction = models.ForeignKey('Reaction', related_name='reaction_abuse', on_delete=models.CASCADE)
    comments = models.TextField('Comments')
    reported_by = models.ForeignKey('users.StargramzUser', related_name='abuse_reported_user', on_delete=models.CASCADE)
    read_flag = models.BooleanField('Verified abuse', default=False)
    created_date = models.DateTimeField('Created Date', auto_now_add=True)

    def __str__(self):
        return 'Abuse reported'
