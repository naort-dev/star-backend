from django.contrib.auth.base_user import BaseUserManager, AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import F
from django.db import connection
from role.models import Role
from utilities.konstants import Konstants, K, ROLES, NOTIFICATION_TYPES as device_notify
from .utils import generate_referral_unique_code, generate_vanity_url
from django.core.validators import MaxValueValidator, MinValueValidator
from .constants import *
from stargramz.models import Stargramrequest, StargramVideo
from .tasks import alert_fans_celebrity_available, alert_admin_celebrity_updates
from django.apps import apps
from django.db.models.signals import pre_save
import datetime
import pytz
from decimal import Decimal
from math import ceil
from django.db.models import Sum
from users.country import COUNTRIES
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericRelation


USER_STATUS = Konstants(
    K(pending=1, label='Pending'),
    K(approved=2, label='Active'),
    K(deleted=3, label='Deleted')
)

GENDER_CHOICES = Konstants(
    K(male=1, label='Male'),
    K(female=2, label='Female'),
)

USER_TYPES = Konstants(
    K(admin=1, label='Admin'),
    K(fan=2, label='Fan'),
    K(celebrity=3, label='Celebrity')
)

SIGN_UP_SOURCE_CHOICES = Konstants(
    K(regular=1, label='Regular Sign-up'),
    K(facebook=2, label='Facebook Sign-up'),
    K(google=3, label='Google Sign-up'),
    K(instagram=4, label='Instagram Sign-up'),
    K(twitter=5, label='Twitter Sign-up'),
)

NOTIFICATION_TYPES = Konstants(
    K(celebrity_starsona_request=1, label='Celebrity Starsona Request'),
    K(celebrity_starsona_message=2, label='Celebrity Starsona Message'),
    K(celebrity_account_updates=3, label='Celebrity Account Updates'),
    K(fan_account_updates=4, label='Fan Account Updates'),
    K(fan_starsona_messages=5, label='Fan Starsona Messages'),
    K(fan_starsona_videos=6, label='Fan Starsona Videos'),
    K(fan_email_starsona_videos=7, label='Fan Email Starsona Videos'),
    K(email_notification=8, label='Email Notification'),
    K(secondary_email=9, label='Secondary Email'),
    K(mobile_country_code=10, label='Mobile Country Code'),
    K(mobile_number=11, label='Mobile Number'),
    K(mobile_notification=12, label='Mobile Notification'),
)

REMINDER_MAIL_COUNT = Konstants(
    K(no_mail=0, label='No Mail'),
    K(first_mail=1, label='First Mail'),
    K(second_mail=2, label='Second Mail'),
)


ACTIVITY_TYPES = Konstants(
    K(comment=1, label='comment'),
    K(reaction=2, label='reaction'),
    K(tip=3, label='tip'),
    K(rating=4, label='rating'),
    K(video=5, label='video')
)


class StargramzUserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, username, password, **extra_fields):
        """
            Creates and saves a User with the given username, email and password.
        """
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, username=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(username, password, **extra_fields)

    def create_superuser(self, username, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(username, password, **extra_fields)


class StargramzUser(AbstractBaseUser, PermissionsMixin):
    username = models.CharField('Username', blank=False, db_index=True, max_length=255, unique=True)
    email = models.EmailField('Email', blank=True, null=True, db_index=True, unique=True)
    first_name = models.CharField('First Name', max_length=128)
    last_name = models.CharField('Last Name', max_length=128, blank=True)
    nick_name = models.CharField('Stage Name', max_length=128, null=True, blank=True)
    status = models.IntegerField('Status', choices=USER_STATUS.choices(), default=USER_STATUS.pending, db_index=True)
    is_staff = models.BooleanField('Staff Status', default=False,
                                   help_text='Designates whether the user can log into this admin site.',
                                   db_index=True)
    is_active = models.BooleanField('Active', default=True,
                                    help_text=('Designates whether this user should be treated as '
                                               'active. Deselect this instead of deleting accounts.'), db_index=True)
    sign_up_source = models.IntegerField('Sign-up Source', choices=SIGN_UP_SOURCE_CHOICES.choices(),
                                         default=SIGN_UP_SOURCE_CHOICES.regular)
    created_date = models.DateTimeField('Created Date', auto_now_add=True)
    modified_date = models.DateTimeField('Modified Date', auto_now=True)
    gender = models.IntegerField('Gender', choices=GENDER_CHOICES.choices(), default=GENDER_CHOICES.male,
                                 db_index=True)
    phone = models.CharField('Phone Number', null=True, blank=True, max_length=15)
    date_of_birth = models.DateField('Date of Birth', null=True, blank=True)
    reset_id = models.UUIDField(default=None, blank=True, null=True)
    reset_generate_time = models.DateTimeField(default=None, blank=True, null=True)
    profile_photo = models.TextField(blank=True, null=True)
    avatar_photo = models.ForeignKey('ProfileImage', blank=True, null=True, related_name='profile_pic', on_delete=models.SET_NULL)
    featured_photo = models.ForeignKey('ProfileImage', blank=True, null=True, related_name='featured_image', on_delete=models.SET_NULL)
    fb_id = models.CharField('Facebook id', max_length=260, blank=True, null=True)
    in_id = models.CharField('Instagram id', max_length=260, blank=True, null=True)
    gp_id = models.CharField('Google Plus id', max_length=260, blank=True, null=True)
    tw_id = models.CharField('Twitter id', max_length=260, blank=True, null=True)
    stripe_customer_id = models.CharField('Stripe Customer ID', max_length=150, blank=True, null=True)
    notification_badge_count = models.IntegerField('Update fcm notification count', default=0)
    show_nick_name = models.BooleanField('Show Stage Name over legal name', default=False)
    unseen_bookings = models.IntegerField('Unseen booking requests count', default=0)
    completed_view_count = models.IntegerField('Completed videos count', default=0)
    order = models.IntegerField('list order', blank=True, null=True)
    referral_active = models.BooleanField('Activate referral for this user', default=False)
    referral_code = models.CharField('Referral Code', max_length=25, blank=True, null=True)
    referral_campaign = models.ForeignKey('Campaign', blank=True, null=True, related_name='campaign', on_delete=models.CASCADE)
    has_requested_referral = models.BooleanField('Referral requested', default=False)
    stripe_user_id = models.CharField('Stripe User ID', max_length=150, blank=True, null=True)
    check_payments = models.BooleanField('Check Payment', default=False)
    group_notification = models.IntegerField('Group invite/support count', default=0)
    admin_approval_referral_code = models.ForeignKey('AdminReferral', blank=True, null=True,
                                                     related_name='admin_referral', on_delete=models.PROTECT)
    ambassador = models.ForeignKey('self', blank=True, null=True, related_name='ambassador_star', on_delete=models.CASCADE)
    is_ambassador = models.BooleanField('Is Ambassador', default=False)
    temp_password = models.BooleanField('Temp Password', default=False)
    expiry_date = models.DateTimeField('Expiry Date', null=True, blank=True)
    reminder_mail_count = models.IntegerField(
        'Reminder Mail count', choices=REMINDER_MAIL_COUNT.choices(), default=REMINDER_MAIL_COUNT.no_mail,
        db_index=True
    )
    server_access_time_stamp = models.DateTimeField('Server access time stamp', null=True, blank=True)

    objects = StargramzUserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = 'user'
        verbose_name_plural = 'users'
        indexes = [
            models.Index(fields=['first_name']),
            models.Index(fields=['last_name']),
            models.Index(fields=['nick_name']),
        ]

    def __str__(self):
        return self.username

    def get_short_name(self):
        """
            Returns the full name for the user.
        """
        if self.nick_name:
            return self.nick_name.title()
        return ' '.join(filter(None, [self.first_name, self.last_name])).title()

    def save(self, *args, **kwargs):
        # Updating the model with username and email
        if self.email:
            self.username = self.email
        if self.username:
            self.email = self.username

        super(StargramzUser, self).save(*args, **kwargs)


def pre_save_generate_referral_code(sender, instance, *args, **kwargs):
    try:
        campaign = Campaign.objects.get(pk=2)
        if not instance.referral_code:
            instance.referral_code = generate_referral_unique_code(instance)
            instance.referral_campaign = campaign
            instance.has_requested_referral = True
            instance.referral_active = True
    except Exception:
        pass



pre_save.connect(pre_save_generate_referral_code, sender=StargramzUser)


@receiver(post_save, sender=StargramzUser)
def update_celebrity_index(sender, instance, **kwargs):
    celebrity = None
    try:
        celebrity = Celebrity.objects.get(user_id=instance.id)
    except:
        pass
    if celebrity and not instance.temp_password:
        index_celebrity(Celebrity, celebrity)


class AdminUser(StargramzUser):
    """
        Proxy Class of Users Model for Admin Users
    """
    class Meta:
        proxy = True


class FanUser(StargramzUser):
    """
        Proxy Class of Users Model for Fans
    """
    class Meta:
        proxy = True


class CelebrityUser(StargramzUser):
    """
        Proxy Class of Users Model for Celebrities
    """
    class Meta:
        proxy = True


class UserRoleMapping(models.Model):
    user = models.ForeignKey(StargramzUser, related_name='stargramz_user', on_delete=models.CASCADE)
    role = models.ForeignKey(Role, related_name='stargramz_role', on_delete=models.CASCADE)
    is_complete = models.BooleanField('Register Completed', default=False)

    class Meta:
        unique_together = ('user', 'role')

    def __str__(self):
        return '%s %s' % (self.user, self.role)


class Profession(models.Model):
    title = models.CharField('title', max_length=250)
    description = models.CharField('description', max_length=350, blank=True, null=True)
    file = models.FileField(blank=True, null=True)
    parent = models.ForeignKey('self', blank=True, null=True, related_name='child', on_delete=models.CASCADE)
    order = models.IntegerField('list order', blank=True, null=True)

    class Meta:
        verbose_name_plural = 'Professions'
        ordering = ['order', 'title']
        indexes = [
            models.Index(fields=['title', 'parent']),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # Adding Impersonators list
        child_lists = []
        impersonators = Profession.objects.filter(parent_id=7).values('id')
        for profession in impersonators:
            child_lists.append(profession['id'])
        with open("users/impersonators.py", mode='w') as file:
            file.truncate()
            file.write('IMPERSONATOR = %s' % str(child_lists))
        super(Profession, self).save(*args, **kwargs)


class Celebrity(models.Model):
    user = models.OneToOneField('StargramzUser', related_name='celebrity_user', blank=False, on_delete=models.CASCADE)
    rate = models.DecimalField('Rate', max_digits=7, decimal_places=2, blank=False)
    in_app_price = models.DecimalField('Inapp Price', max_digits=7, decimal_places=2, blank=True, default=0.00,
                                      null=True)
    rating = models.DecimalField('Celebrity rating', max_digits=4, decimal_places=2, blank=True, default=0.00,
                                 validators=[MinValueValidator(MIN_RATING_VALUE),
                                             MaxValueValidator(MAX_RATING_VALUE)])
    weekly_limits = models.IntegerField('Weekly limits', blank=False)
    profile_video = models.CharField('Profile video', max_length=250, null=True, blank=True)
    duration = models.TimeField('Duration', blank=True, null=True)
    follow_count = models.IntegerField('Followers', default=0, blank=True)
    description = models.TextField('Description', blank=True)
    charity = models.TextField('Charity', blank=True)
    website = models.CharField('Website', max_length=260, blank=True, null=True)
    visibility = models.BooleanField('Visibility', default=True)
    availability = models.BooleanField('Availability', default=True)
    admin_approval = models.BooleanField('Admin Approved', default=False)
    featured = models.BooleanField('Featured', default=False)
    remaining_limit = models.IntegerField('remain limit', blank=True, default=-1)
    created_date = models.DateTimeField('Created date', auto_now_add=True)
    view_count = models.IntegerField('View Count', default=0, blank=True)
    # stripe_user_id need to be removed after the migrations
    stripe_user_id = models.CharField('Stripe User ID', max_length=150, blank=True, null=True)
    check_comments = models.CharField('Check Payment Comments', max_length=300, blank=True, null=True)
    # check_payments need to be removed after the migrations
    check_payments = models.BooleanField('Check Payment', default=False)
    has_fan_account = models.BooleanField('User has fan Account', default=False)
    star_approved = models.BooleanField('Star Approved', default=True)
    migrated = models.BooleanField('Migrated', default=False)
    trending_star_score = models.IntegerField('Star Score', default=0, blank=True)
    average_response_time = models.DecimalField('Average Response Time', max_digits=7, decimal_places=2, blank=True, default=0.00)

    def __str__(self):
        return 'Celebrity Details'

    __original_admin_approval = False

    def __init__(self, *args, **kwargs):
        super(Celebrity, self).__init__(*args, **kwargs)
        self.__original_admin_approval = self.admin_approval
        self.__original_weekly_limits = self.weekly_limits
        self.__original_remaining_limit = self.remaining_limit

    def save(self, *args, **kwargs):
        from notification.tasks import send_notification
        """
            Initalize initial value for remaining_limit and Updation of remaining_limit for a week
        """
        if self.pk is None:
            self.remaining_limit = self.weekly_limits

        if self.__original_weekly_limits != self.weekly_limits:
            """
                Update the remaining limits based on weekly limits and total request in a week
            """
            # Get the total bookings of the celebrity
            total_requests = Stargramrequest.objects.filter(
                celebrity_id=self.user_id,
                request_status__in=[1, 2, 3]
                ).count()

            pending_total = int(self.weekly_limits) - int(total_requests)
            self.remaining_limit = pending_total if pending_total > 0 else 0
        if self.availability and self.remaining_limit > 0 and (self.__original_remaining_limit != self.remaining_limit):
            alert_fans_celebrity_available.delay(self.user_id)
        if self.__original_admin_approval != self.admin_approval and self.admin_approval:
            alert_admin_celebrity_updates.delay(self.user_id, 3)
            # Notify user via push notification
            data = {'id': self.user_id, 'type': device_notify.alert_celebrity_approval,
                    'role': ROLES.celebrity}
            send_notification.delay(self.user_id,
                                    NOTIFICATION_APPROVE_CELEBRITY_TITLE,
                                    NOTIFICATION_APPROVE_CELEBRITY_BODY,
                                    data, field='celebrity_account_updates')
        super(Celebrity, self).save(*args, **kwargs)

    def indexing(self):
        from versioned.v2.users.search import celebrity_indexing

        return celebrity_indexing(self)


@receiver(post_save, sender=Celebrity)
def index_celebrity(sender, instance, **kwargs):
    from versioned.v2.users.search import get_elasticsearch_connection_params, connections, Elasticsearch, \
        Celebrities, ES_CELEBRITY_INDEX

    if instance.admin_approval and instance.availability and instance.star_approved and not instance.user.temp_password:
        connection_params = get_elasticsearch_connection_params()
        connections.create_connection(**connection_params)
        Elasticsearch(**connection_params)
        Celebrities.init(index=ES_CELEBRITY_INDEX)
        instance.indexing()


@receiver(post_save, sender=Celebrity)
def update_bio_in_dashboard(sender, instance, **kwargs):
    from versioned.v2.users.models import CelebrityDashboard
    from versioned.v2.users.utils import biography_referral_update
    try:
        dashboard = CelebrityDashboard.objects.get(user_id=instance.user.id)
        biography_referral_update(dashboard)
    except Exception as e:
        print(str(e))
        pass


class ProfessionsManager(models.Manager):
    def get_queryset(self):
        with connection.cursor() as cursor:
            cursor.execute("select DISTINCT p.parent_id from users_profession p JOIN users_celebrityprofession cp "
                           "ON cp.profession_id = p.id where p.parent_id is NOT NULL")
            return [key[0] for key in cursor.fetchall()]


class CelebrityProfession(models.Model):
    user = models.ForeignKey('StargramzUser', related_name='celebrity_profession', blank=False, on_delete=models.CASCADE)
    profession = models.ForeignKey('Profession', related_name='profession', blank=False, on_delete=models.CASCADE)
    created_date = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    active_professions = ProfessionsManager()


class ProfileImage(models.Model):
    user = models.ForeignKey('StargramzUser', related_name='images', on_delete=models.CASCADE)
    photo = models.CharField('Upload Image', max_length=600, null=True, blank=True)
    status = models.BooleanField(default=True)
    created_date = models.DateTimeField('Created Date', auto_now_add=True)
    thumbnail = models.CharField('Thumbnail Image', max_length=600, null=True, blank=True)
    medium_thumbnail = models.CharField('Medium Thumbnail Image', max_length=600, null=True, blank=True)

    def __str__(self):
        return self.photo

    class Meta:
        ordering = ['id']


class RecentActivity(models.Model):
    activity_from_user = models.ForeignKey('StargramzUser', related_name='activity_from', on_delete=models.CASCADE)
    activity_to_user = models.ForeignKey('StargramzUser', related_name='activity_to', on_delete=models.CASCADE)
    request = models.ForeignKey('stargramz.Stargramrequest', related_name='activity_request', on_delete=models.CASCADE)
    activity_type = models.IntegerField('Activity Type', choices=ACTIVITY_TYPES.choices(), default=ACTIVITY_TYPES.comment)
    created_date = models.DateTimeField('Created Date', auto_now_add=True)
    is_celebrity_activity = models.BooleanField('Is Celebrity Activity', default=False)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    public_visibility = models.BooleanField('Public Visibility', default=True)


class FanRating(models.Model):
    fan = models.ForeignKey(StargramzUser, on_delete=models.CASCADE, related_name='fan_rate_user')
    celebrity = models.ForeignKey(StargramzUser, on_delete=models.CASCADE, related_name='celebrity_rate_user')
    fan_rate = models.DecimalField('Fan rating', max_digits=4, decimal_places=2, blank=True, default=0.00,
                                   validators=[MinValueValidator(MIN_RATING_VALUE),
                                               MaxValueValidator(MAX_RATING_VALUE)])
    starsona = models.ForeignKey(Stargramrequest, related_name='request_rating', on_delete=models.CASCADE)
    reason = models.CharField('Reason', max_length=260, blank=True)
    comments = models.CharField('Comments', max_length=260, blank=True)
    created_date = models.DateTimeField('Created date', auto_now_add=True)
    activities = GenericRelation(RecentActivity)

    def __str__(self):
        return 'Fan Rating for Booking - %s' % self.starsona_id


@receiver(post_save, sender=FanRating)
def create_rating_activity(sender, instance, **kwargs):
    if instance.fan == instance.starsona.celebrity:
        activity = RecentActivity(
            content_object=instance, activity_from_user=instance.fan, activity_to_user=instance.starsona.fan,
            request=instance.starsona, activity_type=ACTIVITY_TYPES.rating, is_celebrity_activity=True,
            public_visibility=False
        )
    else:
        activity = RecentActivity(
            content_object=instance, activity_from_user=instance.fan, activity_to_user=instance.celebrity,
            request=instance.starsona, activity_type=ACTIVITY_TYPES.rating, is_celebrity_activity=False,
            public_visibility=False
        )
        instance.starsona.recent_activity_date = datetime.datetime.now(pytz.UTC)
        instance.starsona.save()
    activity.save()


@receiver(post_save, sender=FanRating)
def save_rating_count(sender, instance, **kwargs):
    total_user = FanRating.objects.filter(celebrity_id=instance.celebrity_id)
    fan_count = Decimal(total_user.count())
    total_sum_rating = total_user.aggregate(Sum('fan_rate'))
    avg_rating = round(total_sum_rating['fan_rate__sum'] / fan_count, 1)
    round_off_avg = 0.5 * ceil(2.0 * float(avg_rating))
    # Updating the celebrity avg comment counts
    Celebrity.objects.filter(user_id=instance.celebrity_id).update(rating=round_off_avg)
    # Updating video read status at the time of submitting rating
    StargramVideo.objects.filter(stragramz_request_id=instance.starsona).update(read_status=True)


@receiver(post_save, sender=FanRating)
def update_rating_in_dashboard(sender, instance, **kwargs):
    from versioned.v2.users.models import CelebrityDashboard
    from versioned.v2.users.utils import rating_data_update
    try:
        dashboard = CelebrityDashboard.objects.get(user_id=instance.celebrity.id)
        rating_data_update(dashboard)
    except Exception as e:
        print(str(e))
        pass


class CelebrityFollow(models.Model):
    celebrity = models.ForeignKey('StargramzUser', related_name='celebrity_follow', on_delete=models.CASCADE)
    fan = models.ForeignKey('StargramzUser', related_name='fan_user_follow', on_delete=models.CASCADE)
    is_group = models.BooleanField('Is Group account', default=False)
    created_date = models.DateTimeField('Created Date', auto_now_add=True)


class CelebrityView(models.Model):
    celebrity = models.ForeignKey('StargramzUser', related_name='celebrity_view', on_delete=models.CASCADE)
    fan = models.ForeignKey('StargramzUser', related_name='fan_user_view', on_delete=models.CASCADE)
    created_date = models.DateTimeField('Created Date', auto_now_add=True)


@receiver(post_save, sender=CelebrityView)
def save_profile_view_count(sender, instance, **kwargs):
    Celebrity.objects.filter(user_id=instance.celebrity_id).update(view_count=F('view_count') + 1)
    Celebrity.objects.filter(user_id=instance.celebrity_id).update(trending_star_score=F('trending_star_score') + 1)


class CelebrityAbuse(models.Model):
    celebrity = models.ForeignKey('StargramzUser', related_name='celebrity_abuse', on_delete=models.CASCADE)
    fan = models.ForeignKey('StargramzUser', related_name='fan_user_abuse', on_delete=models.CASCADE)
    abuse_comment = models.CharField(max_length=260)
    created_date = models.DateTimeField('Created Date', auto_now_add=True)
    status = models.BooleanField(default=False)


class DeviceTokens(models.Model):
    user = models.ForeignKey('StargramzUser', related_name='device_user', on_delete=models.CASCADE)
    device_type = models.CharField('Device Type', max_length=50)
    device_id = models.CharField('Device ID', max_length=255)
    device_token = models.CharField('Device Token', max_length=255)
    created_date = models.DateTimeField('Created Date', auto_now_add=True)


class Notifications(models.Model):
    user = models.ForeignKey('StargramzUser', related_name='notification_user', on_delete=models.CASCADE)
    notification_type = models.IntegerField('Notification Type', choices=NOTIFICATION_TYPES.choices(), db_index=True)
    message_title = models.CharField('Message title', max_length=100)
    message_content = models.CharField('Message Content', max_length=255)
    status = models.BooleanField(default=False)
    created_date = models.DateTimeField('Created Date', auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)


class SettingsNotifications(models.Model):
    user = models.ForeignKey('StargramzUser', related_name='settings_user', on_delete=models.CASCADE)
    celebrity_starsona_request = models.BooleanField(default=True)
    celebrity_starsona_message = models.BooleanField(default=True)
    celebrity_account_updates = models.BooleanField(default=True)
    fan_account_updates = models.BooleanField(default=True)
    fan_starsona_messages = models.BooleanField(default=True)
    fan_starsona_videos = models.BooleanField(default=True)
    fan_email_starsona_videos = models.BooleanField(default=True)
    email_notification = models.BooleanField(default=False)
    secondary_email = models.EmailField(blank=True, null=True)
    mobile_country_code = models.CharField(blank=True, null=True, max_length=5)
    mobile_number = models.CharField(blank=True, null=True, max_length=15)
    mobile_notification = models.BooleanField(default=False)
    mobile_verified = models.BooleanField(default=False)
    verification_uuid = models.CharField(blank=True, null=True, max_length=120)
    is_viewed = models.BooleanField(default=False)


class CelebrityAvailableAlert(models.Model):
    celebrity = models.ForeignKey('StargramzUser', related_name='alert_celebrity', on_delete=models.CASCADE)
    fan = models.ForeignKey('StargramzUser', related_name='alert_fan', on_delete=models.CASCADE)
    notification_send = models.BooleanField('Notification Send', default=False)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)


class Campaign(models.Model):
    title = models.CharField('Campaign Title', max_length=100)
    description = models.CharField('Campaign Description', max_length=255)
    discount = models.IntegerField('Referral revenue (%)', default=0)
    enable_two_way = models.BooleanField('Enable two way rewards', default=False,
                                         help_text="Referee can avail 100% revenue*")
    valid_from = models.DateField('Campaign Valid from')
    valid_till = models.DateField('Campaign Valid to')
    valid_for_days = models.IntegerField('No of days referral can earn')
    request_for_user = models.IntegerField('No of requests for which referred person can avail 100% revenue')
    max_referral_amount = models.IntegerField('Maximum referral amount referrer can earn')
    created_date = models.DateTimeField('Created Date', auto_now_add=True)

    def __str__(self):
        return self.title


class Referral(models.Model):
    referrer = models.ForeignKey('StargramzUser', related_name='refer_referrer', on_delete=models.CASCADE)
    referee = models.ForeignKey('StargramzUser', related_name='refer_referee', on_delete=models.CASCADE)
    source = models.CharField('Source', max_length=100)
    created_date = models.DateTimeField('Created Date', auto_now_add=True)

    def __str__(self):
        return 'Referral ID %d' % self.pk

@receiver(post_save, sender=Referral)
def update_referral_in_dashboard(sender, instance, **kwargs):
    from versioned.v2.users.models import CelebrityDashboard
    from versioned.v2.users.utils import biography_referral_update
    try:
        dashboard = CelebrityDashboard.objects.get(user_id=instance.celebrity.id)
        biography_referral_update(dashboard)
    except Exception as e:
        print(str(e))
        pass


class VanityUrl(models.Model):
    name = models.CharField('Name', unique=True, max_length=100)
    user = models.OneToOneField('StargramzUser', related_name='vanity_urls', blank=False, on_delete=models.CASCADE)
    created_date = models.DateTimeField('Created Date', auto_now_add=True)


@receiver(post_save, sender=StargramzUser)
def execute_after_save(sender, instance, created, *args, **kwargs):
    if created and kwargs['using'] == 'default':
        count = 0
        try:
            if kwargs.get('count'):
                count = int(kwargs.get('count')) + 1
        except Exception:
            pass
        code = generate_vanity_url(instance, count)
        try:
            VanityUrl.objects.create(name=code, user=instance)
        except Exception:
            count = count+1
            execute_after_save(sender, instance, created, count=count)


class GroupType(models.Model):
    group_name = models.CharField('Group name', max_length=260, blank=True, null=True)
    order = models.IntegerField('list order', blank=True, null=True)
    active = models.BooleanField('Active', default=True)
    created_date = models.DateTimeField('Created date', auto_now_add=True)
    modified_date = models.DateTimeField('Modified date', auto_now=True)

    def __str__(self):
        return self.group_name


class GroupAccount(models.Model):
    user = models.OneToOneField('StargramzUser', related_name='group_account', blank=False, on_delete=models.CASCADE)
    contact_first_name = models.CharField('Contact first name', max_length=260, blank=True, null=True)
    contact_last_name = models.CharField('Contact last name', max_length=260, blank=True, null=True)
    follow_count = models.IntegerField('Followers', default=0, blank=True)
    group_type = models.ForeignKey(GroupType, related_name='group_account_type', blank=False, on_delete=models.CASCADE)
    description = models.TextField('Description', blank=True)
    tags = models.CharField('Tags', max_length=260, blank=True, null=True)
    website = models.CharField('Website', max_length=260, blank=True, null=True)
    phone = models.CharField('Phone Number', null=True, blank=True, max_length=15)
    address = models.CharField('Address', max_length=260, blank=True, null=True)
    address_2 = models.CharField('Address 2', max_length=260, blank=True, null=True)
    city = models.CharField('City', max_length=200, blank=True, null=True)
    state = models.CharField('State', max_length=200, blank=True, null=True)
    zip = models.IntegerField('Zip', blank=True, null=True)
    country = models.IntegerField('Country', choices=COUNTRIES.choices(), db_index=True, default=-1)
    admin_approval = models.BooleanField('Admin Approved', default=False)
    created_date = models.DateTimeField('Created date', auto_now_add=True)
    modified_date = models.DateTimeField('Modified date', auto_now=True)

    def __str__(self):
        return self.user.get_short_name()

    def get_grouptype(self):
        return str(self.group_type)


@receiver(post_save, sender=GroupAccount)
def group_created_notification(sender, instance, created, **kwargs):
    from config.models import Config
    from job.tasks import send_message_to_slack
    if created:
        web_url = Config.objects.get(key="web_url").value
        slack_template = "new_user_group"
        slack_ctx = {
            "group_name": instance.user.get_short_name(),
            "group_link": "%sgroup-profile/%s" % (web_url, instance.user.vanity_urls.name)
        }
        send_message_to_slack.delay(slack_template, slack_ctx)


class GroupAccountUser(StargramzUser):
    """
        Proxy Class of Users Model for Admin Users
    """
    class Meta:
        verbose_name_plural = 'Brand/Charity'
        proxy = True


class CelebrityGroupAccount(models.Model):
    user = models.ForeignKey('StargramzUser', related_name='celebrity_account', blank=False, on_delete=models.CASCADE)
    account = models.ForeignKey('StargramzUser', related_name='account_user', blank=False, on_delete=models.CASCADE)
    approved = models.BooleanField('Admin Approved', default=False)
    celebrity_invite = models.BooleanField('Celebrity Invitation', default=False)
    order = models.IntegerField('list order', blank=True, null=True)
    created_date = models.DateTimeField('Created date', auto_now_add=True)
    modified_date = models.DateTimeField('Modified date', auto_now=True)

    class Meta:
        unique_together = (("user", "account"),)
        verbose_name = 'Join Group'
        verbose_name_plural = 'Join Groups'

    def __str__(self):
        return self.user.get_short_name()


@receiver(post_save, sender=CelebrityGroupAccount)
def group_notification_updater(sender, instance, created, **kwargs):
    if created:
        if instance.approved:
            instance.user.group_notification = F('group_notification') + 1
            instance.user.save()
        elif instance.celebrity_invite:
            instance.account.group_notification = F('group_notification') + 1
            instance.account.save()


class SocialMediaLinks(models.Model):
    user = models.ForeignKey('StargramzUser', related_name='user_social_links', blank=False, on_delete=models.CASCADE)
    social_link_key = models.CharField('Social media name', blank=False, max_length=255)
    social_link_value = models.CharField('Social media URL', blank=True, max_length=255)
    created_date = models.DateTimeField('Created date', auto_now_add=True)
    modified_date = models.DateTimeField('Modified date', auto_now=True)

    def __str__(self):
        return self.user.get_short_name()


class Representative(models.Model):
    celebrity = models.ForeignKey('StargramzUser', related_name='celebrity_representative', blank=False, on_delete=models.CASCADE)
    first_name = models.CharField('First Name', max_length=128)
    last_name = models.CharField('Last Name', max_length=128, blank=True, null=True)
    email = models.EmailField('Email', blank=True, null=True, db_index=True)
    phone = models.CharField('Phone Number', blank=True, null=True, max_length=15)
    country_code = models.CharField('Country Code', blank=True, null=True, max_length=5)
    email_notify = models.BooleanField('Email Notify', default=False)
    email_verified = models.BooleanField('Email Verified', default=False)
    sms_notify = models.BooleanField('SMS Notify', default=False)
    sms_verified = models.BooleanField('SMS Verified', default=False)
    created_date = models.DateTimeField('Created date', auto_now_add=True)
    modified_date = models.DateTimeField('Modified date', auto_now=True)

    def __str__(self):
        return 'Celebrity Representative'


class TwitterKey(models.Model):
    resource_owner_key = models.CharField(max_length=128)
    resource_owner_secret = models.CharField(max_length=128)
    created_date = models.DateTimeField('Created date', auto_now_add=True)


class AdminReferral(models.Model):
    referral_code = models.CharField("Referral code", max_length=100)
    activate = models.BooleanField("Activate", default=True)
    created_date = models.DateTimeField('Created date', auto_now_add=True)

    def __str__(self):
        return self.referral_code
