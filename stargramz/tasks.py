from __future__ import absolute_import, unicode_literals
from main.celery import app
from django.db.models import Q
from .models import Stargramrequest, STATUS_TYPES, REQUEST_TYPES
from users.models import VanityUrl
from django.utils import timezone
import datetime
from notification.tasks import send_notification
from utilities.konstants import NOTIFICATION_TYPES, ROLES
from .constants import *
from payments.tasks import create_request_refund
from payments.models import PAYMENT_TYPES
from config.models import Config
from config.constants import *
from utilities.utils import SendMail, generate_branch_io_url, sent_email, encode_pk
from django.template.loader import get_template
from hashids import Hashids
import pytz
import json
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
        (
                Q(request_transaction__payment_type=PAYMENT_TYPES.stripe) &
                Q(request_transaction__ambassador_transaction=False) &
                Q(created_date__lt=timezone.now() - datetime.timedelta(days=REQUEST_CANCEL_DAYS))
        ) |
        (
                Q(request_transaction__payment_type=PAYMENT_TYPES.in_app) &
                Q(request_transaction__ambassador_transaction=False) &
                Q(created_date__lt=timezone.now() - datetime.timedelta(days=REQUEST_CANCEL_DAYS_INAPP))
        )
    )
    non_expiring_request_count = Stargramrequest.objects.filter(
        Q(request_status__in=[2, 3]) &
        (
                (
                        Q(created_date__gt=timezone.now() - datetime.timedelta(days=REQUEST_CANCEL_DAYS)) &
                        Q(request_transaction__payment_type=PAYMENT_TYPES.stripe)
                ) |
                (
                        Q(created_date__gt=timezone.now() - datetime.timedelta(days=REQUEST_CANCEL_DAYS_INAPP)) &
                        Q(request_transaction__payment_type=PAYMENT_TYPES.in_app)
                )
        )
    ).count()
    for request in requests:
        print(request.id)
        if request.celebrity.unseen_bookings > 0:
            if request.celebrity.unseen_bookings > non_expiring_request_count:
                request.celebrity.unseen_bookings = request.celebrity.unseen_bookings - 1
                request.celebrity.save()
        Stargramrequest.objects.filter(pk=request.id).update(
            request_status=STATUS_TYPES.cancelled,
            comment=REQUEST_CANCEL_COMMENT
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

        admin_email = Config.objects.get(key='admin_email').value
        ctx = {'requests': request_counts}
        # notify_email replaced with send email
        sent_email(admin_email, 'Pending Video approvals', 'pending_video_approval', ctx)
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
            # cancel_starsona_celebrity_no_response.apply_async(
            #    eta=datetime.datetime.utcnow() + datetime.timedelta(
            #        hours=hours,
            #        minutes=minutes
            #    )
            #)
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
    celebrity_email = celebrity.user.email
    # notify_email replaced with send email
    sent_email(celebrity_email, 'Request limit reached', 'celebrity_request_limit', ctx)


@app.task
def booking_feedback_celebrity_notification(booking_id, fields):
    from job.tasks import send_sms_celebrity

    try:
        base_url = Config.objects.get(key='base_url').value
        web_url = Config.objects.get(key='web_url').value
        booking = Stargramrequest.objects.get(id=booking_id)
        mob_link = 'request/?request_id=%s&role=R1002' % encode_pk(booking.id)
        ctx = {
            "fan_name": booking.fan.get_short_name(),
            "celebrity_name": booking.celebrity.get_short_name(),
            "fan_rating": fields.get("fan_rate", 0.0),
            "comments": fields.get("comments", None),
            "app_url": generate_branch_io_url(
                title="New reaction received",
                desc="Fan %s Reacted to your Starsona video." % booking.fan.get_short_name(),
                mob_url=mob_link,
                desktop_url='%suser/bookings?request_id=%s' % (web_url, encode_pk(booking.id)),
                image_url='%smedia/web-images/starsona_logo.png' % base_url,
                nav_to='reactions',
                canonical_url="%srequest/R1002/%s" % (web_url, encode_pk(booking.id))
            )
        }
        template = "feedback_notification"
        to_email = booking.celebrity.email
        subject = "New Reaction from %s" % booking.fan.get_short_name()
        sent_email(to_email, subject, template, ctx)

        message = "%s has reacted to your video. To view the rating and comments click: %s" % (
            booking.fan.get_short_name(), ctx.get("app_url")
        )
        send_sms_celebrity.delay(message, booking.celebrity.id)
        return True
    except Exception:
        return False


@app.task(name='celebrity_request_notification')
def celebrity_request_notification():
    """
    This task will send reminder mail to all the celebrity who has not completed their Starsona request
    :return:
    """
    requests = Stargramrequest.objects.filter(request_status__in=[2, 3])
    try:
        days = Config.objects.get(key='celebrity_notify_days').value
        days = [int(i) for i in days.replace(',', '')]
        current_date = datetime.datetime.now(pytz.utc).date()
        web_url = Config.objects.get(key='web_url').value
        base_url = Config.objects.get(key='base_url').value
        for request in requests:
            if (current_date - request.created_date.date()).days in days:
                expiring_date = (request.created_date + datetime.timedelta(days=7)).date()
                # mobile redirection issue fix
                # mob_link = 'request/?request_id=%s' % encode_pk(request.id)
                mob_link = 'request/?request_id=%s&role=R1002' % encode_pk(request.id)
                if current_date == expiring_date:
                    subject = 'Reminder: Pending Starsona {} Request - EXPIRES TODAY!'.format(request.occasion.title)
                    template = 'reminder_emails/request_expiry_notification'
                else:
                    if (expiring_date - current_date).days == ONE:
                        subject = 'Reminder: Pending Starsona {} Request - EXPIRES TOMORROW!'.format(
                            request.occasion.title
                        )
                        template = 'reminder_emails/event_announcement_request_notification' \
                            if request.request_type == REQUEST_TYPES.event_announcement \
                            else 'reminder_emails/shout_out_request_expire_tomorrow_notification'
                    else:
                        subject = 'Reminder: Pending Starsona {} Request'.format(request.occasion.title)
                        template = 'reminder_emails/event_announcement_request_notification' \
                            if request.request_type == REQUEST_TYPES.event_announcement \
                            else 'reminder_emails/shout_out_request_notification'
                request_data = json.loads(request.request_details) if request.request_details else ''
                ctx = {
                    "celebrity_name": request.celebrity.get_short_name(),
                    "fan_name": request.fan.get_short_name(),
                    "booking_title": request.booking_title,
                    "occasion": request.occasion.title,
                    "expiring_date": expiring_date.strftime('%B %d, %Y'),
                    "app_url": generate_branch_io_url(
                        title="Request reminder",
                        desc="Reminder of the Starsona Request from %s." % request.fan.get_short_name(),
                        mob_url=mob_link,
                        desktop_url='%suser/bookings' % web_url,
                        canonical_url='%srequest/R1002/%s' % (web_url, encode_pk(request.id)),
                        image_url='%smedia/web-images/starsona_logo.png' % base_url
                    ),
                    'relationship': request_data['relationship']['title'] if 'relationship' in request_data else '',
                    'important_info': request_data['important_info'] if 'important_info' in request_data else '',
                    'to_name': request_data['stargramto'] if 'stargramto' in request_data else '',
                    'from_name': request_data['stargramfrom'] if 'stargramfrom' in request_data else '',
                    'date': datetime.datetime.strptime(
                        request_data['date'], "%Y-%m-%dT%H:%M:%S.%fZ"
                    ).strftime('%B %d, %Y') if ('date' in request_data and request_data['date']) else '',
                    'event_title': request_data['event_title'] if 'event_title' in request_data else '',
                    'expire_tomorrow': True if (expiring_date - current_date).days == ONE else False,
                    'live_qa_request': True if request.request_type == REQUEST_TYPES.live_question_answer else False
                }
                sent_email(request.celebrity.email, subject, template, ctx)
        return True
    except Exception as e:
        return False
