from __future__ import absolute_import, unicode_literals
from main.celery import app
from celery import shared_task
from django.db.models import Q
from .models import Stargramrequest, STATUS_TYPES, Reaction, StargramVideo
from users.models import VanityUrl
from django.utils import timezone
import datetime
from notification.tasks import send_notification
from utilities.konstants import NOTIFICATION_TYPES, ROLES
from .constants import *
from payments.tasks import create_request_refund
from config.models import Config
from config.constants import *
from utilities.utils import SendMail, generate_branch_io_url, get_bucket_url
from django.template.loader import get_template
from job.tasks import notify_email
from hashids import Hashids
import pytz
hashids = Hashids(min_length=8)


@app.task(name='notification_request_remainder')
def send_notifications_reminder(from_date, to_date):
    print('Send Notification with %s days request in pending status' % (from_date if from_date == 5 else to_date))
    requests = Stargramrequest.objects.filter(Q(request_status__in=[2, 3]) &
                                              Q(created_date__lte=timezone.now()-datetime.timedelta(days=from_date)) &
                                              Q(created_date__gte=timezone.now()-datetime.timedelta(days=to_date)))
    for request in requests:
        print(request.id)
        data = {'id': request.id, 'type': NOTIFICATION_TYPES.celebrity_booking_open_details,
                'role': ROLES.celebrity}
        send_notification.delay(request.celebrity.id,
                                NOTIFICATION_REQUEST_FIVE_DAY_TITLE if from_date == 5
                                else NOTIFICATION_REQUEST_SEVEN_DAY_TITLE,
                                NOTIFICATION_REQUEST_FIVE_DAY_BODY if from_date == 5
                                else NOTIFICATION_REQUEST_SEVEN_DAY_BODY,
                                data,
                                field='celebrity_starsona_request'
                                )
    return True


@app.task(name='cancel_notification_no_response')
def cancel_starsona_celebrity_no_response():
    print('Cancel request in %s Days' % REQUEST_CANCEL_DAYS)
    requests = Stargramrequest.objects.filter(
        Q(request_status__in=[2, 3]) &
        Q(created_date__lt=timezone.now() - datetime.timedelta(days=REQUEST_CANCEL_DAYS)))
    for request in requests:
        print(request.id)
        Stargramrequest.objects.filter(pk=request.id).update(
            request_status=STATUS_TYPES.cancelled,
            comment=REQUEST_CANCEL_COMMENT % request.celebrity.get_short_name()
        )
        create_request_refund.delay()
        data = {'id': request.id, 'type': NOTIFICATION_TYPES.fan_myvideos_completed_details,
                'role': ROLES.fan}
        send_notification.delay(request.fan.id,
                                NOTIICATION_AUTOMATIC_CANCEL_TITLE,
                                NOTIICATION_AUTOMATIC_CANCEL_BODY,
                                data, field='fan_starsona_videos')

        subject = "We're so sorry!"
        sender_email = Config.objects.get(key='sender_email').value
        base_url = Config.objects.get(key='base_url').value
        web_url = Config.objects.get(key='web_url').value

        try:
            vanity_url = VanityUrl.objects.values_list('name', flat=True).get(user_id=request.celebrity.id)
        except Exception:
            vanity_url = ''

        ctx = {
            'base_url': base_url,
            'celebrity_name': request.celebrity.get_short_name(),
            'fan_name': request.fan.get_short_name(),
            'id': hashids.encode(request.celebrity.id),
            'app_url': generate_branch_io_url(
                title="%s was unable to fulfill your booking request" % request.celebrity.get_short_name(),
                desc="%s was unable to fulfill your booking request." % request.celebrity.get_short_name(),
                mob_url='profile/?profile_id=%s' % vanity_url,
                desktop_url='%s%s' % (web_url, vanity_url),
                image_url='%smedia/web-images/starsona_logo.png' % base_url,
            )
        }
        html_template = get_template('../templates/emails/request_cancellation_expiry.html')
        html_content = html_template.render(ctx)

        try:
            SendMail(subject, html_content, sender_email=sender_email, to=request.fan.email)
        except Exception as e:
            print(str(e))
    return True


@app.task(name='notify_admin_video_approvals')
def notify_admin_approvals():
    """
        Notify Admin for the Pending video approvals
    """
    request_counts = Stargramrequest.objects.filter(Q(request_status=7)).count()

    if request_counts > 0:

        sender_email = Config.objects.get(key='sender_email').value
        admin_email = Config.objects.get(key='admin_email').value
        ctx = {'requests': request_counts}
        notify_email(sender_email, admin_email, 'Pending Video approvals', 'pending_video_approval', ctx)
        print('Notified admin on pending video approvals')
    else:
        print('No pending video approvals')


@app.task(name='cancel_booking_on_seven_days_completion')
def cancel_booking_on_seven_days_completion():
    utc = pytz.UTC
    print('Cancelling booking on time with stripe.')
    requests = Stargramrequest.objects.values_list('request_transaction__created_date', flat=True).filter(
        request_status__in=[2, 3],
        request_transaction__created_date__lt=datetime.datetime.utcnow() - datetime.timedelta(days=6)
    )

    for request in requests:
        scheduled_time = request + datetime.timedelta(days=7)
        estimated = scheduled_time.replace(tzinfo=utc) - datetime.datetime.utcnow().replace(tzinfo=utc)
        hours = estimated.seconds//3600
        minutes = (estimated.seconds//60) - (hours * 60)
        if scheduled_time > timezone.now() and estimated.days >= 0:
            print("Cancel request in %d hours %d minutes" % (hours, minutes))
            cancel_starsona_celebrity_no_response.apply_async(
                eta=datetime.datetime.utcnow() + datetime.timedelta(
                    hours=hours,
                    minutes=minutes
                )
            )
    print("Completed %d booking cancel process" % len(requests))
    return True


def request_limit_notification(celebrity):
    """
        Notify the celebrity when the stargramz request reaches the celebrity weekly limits
    """
    data = {'type': NOTIFICATION_TYPES.request_limit_reached,
            'role': ROLES.celebrity}
    send_notification.delay(celebrity.user.id,
                            NOTIFICATION_REQUEST_LIMIT_TITLE,
                            NOTIFICATION_REQUEST_LIMIT_BODY,
                            data)
    base_url = Config.objects.get(key='base_url').value
    web_url = Config.objects.get(key='web_url').value
    ctx = {'celebrity_name': celebrity.user.get_short_name(),
           'app_url': generate_branch_io_url(
                title="Starsona request limit reached",
                desc="The number of Starsona requests has reached its limits.",
                canonical_url='%sapplinks/set_weekly_limit' % base_url,
                mob_url='set_weekly_limit',
                desktop_url='%ssettings' % web_url,
                image_url='%smedia/web-images/starsona_logo.png' % base_url,
            )}
    sender_email = Config.objects.get(key='sender_email').value
    celebrity_email = celebrity.user.email
    notify_email(sender_email, celebrity_email, 'Request limit reached', 'celebrity_request_limit', ctx)


@shared_task(bind=True, max_retries=1)
def notify_fan_reaction_videos_and_feedback(booking_id):
    """
    Triggering Push/email notifications to fan to add review and share there reaction
    videos with starsona for completed bookings
    :param booking_id:
    :return:
    """
    print("Reaction for %d" % booking_id)
    if Reaction.objects.filter(booking_id=booking_id).count() == 0:
        print('Adding reactions...')
        try:
            requests = Stargramrequest.objects.get(id=booking_id)
        except Exception:
            return True
        booking_hash_id = hashids.encode(booking_id)
        data = {'type': NOTIFICATION_TYPES.pending_reaction_video, 'role': ROLES.fan, 'id': booking_hash_id}
        send_notification.delay(
            requests.fan_id,
            PENDING_REACTION_VIDEO_TITLE,
            PENDING_REACTION_VIDEO_BODY % requests.celebrity.get_short_name(),
            data,
            field='celebrity_starsona_request'
        )
        video = StargramVideo.objects.get(stragramz_request_id=booking_id, status=1)

        base_url = Config.objects.get(key='base_url').value
        web_url = Config.objects.get(key='web_url').value
        ctx = {'celebrity_name': requests.celebrity.get_short_name(),
               'fan_name': requests.fan.get_short_name(),
               'booking_title': requests.booking_title,
               'video_thumb': '{}/{}'.format(get_bucket_url(), STARGRAM_VIDEO_THUMB + video.thumbnail),
               'app_url': generate_branch_io_url(
                    title="Add reaction videos",
                    desc="Add review and share your reaction videos",
                    canonical_url='%sapplinks/reactions/%s' % (base_url, booking_hash_id),
                    mob_url='reactions/%s' % booking_hash_id,
                    desktop_url='%suser/myVideos' % web_url,
                    image_url='%smedia/web-images/starsona_logo.png' % base_url,
                )}
        sender_email = Config.objects.get(key='sender_email').value
        fan_email = requests.fan.email
        notify_email(sender_email, fan_email, 'Add Reaction videos', 'add_reaction_videos', ctx)
        print('Notified fan for reaction videos')
        return True
    else:
        print('Already added reactions')
        return True
