from __future__ import absolute_import, unicode_literals
from main.celery import app
from django.db.models import Q
from .models import Stargramrequest, STATUS_TYPES
from django.utils import timezone
import datetime
from notification.tasks import send_notification
from utilities.konstants import NOTIFICATION_TYPES, ROLES
from .constants import NOTIFICATION_REQUEST_FIVE_DAY_BODY, NOTIFICATION_REQUEST_FIVE_DAY_TITLE, \
    NOTIFICATION_REQUEST_SEVEN_DAY_TITLE, NOTIFICATION_REQUEST_SEVEN_DAY_BODY, REQUEST_CANCEL_DAYS, \
    REQUEST_CANCEL_COMMENT, NOTIICATION_AUTOMATIC_CANCEL_TITLE, NOTIICATION_AUTOMATIC_CANCEL_BODY
from payments.tasks import create_request_refund
from config.models import Config
from utilities.utils import SendMail
from django.template.loader import get_template
from job.tasks import notify_email
from hashids import Hashids
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
        Q(created_date__lt=timezone.now() - datetime.timedelta(days=REQUEST_CANCEL_DAYS)) &
        Q(created_date__gt=timezone.now() - datetime.timedelta(days=REQUEST_CANCEL_DAYS+1)))
    for request in requests:
        print(request.id)
        request.request_status = STATUS_TYPES.cancelled
        request.comment = REQUEST_CANCEL_COMMENT % request.celebrity.get_short_name()
        request.save()
        request.refresh_from_db()
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
        ctx = {
            'base_url': base_url,
            'celebrity_name': request.celebrity.get_short_name(),
            'fan_name': request.fan.get_short_name(),
            'id': hashids.encode(request.celebrity.id)
        }

        html_template = get_template('../templates/emails/request_cancellation_expiry.html')
        html_content = html_template.render(ctx)

        try:
            SendMail(subject, html_content, sender_email=sender_email, to=request.fan.email)
        except Exception as e:
            print(str(e))


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
