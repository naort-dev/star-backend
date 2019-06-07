from __future__ import absolute_import, unicode_literals
import os
from django.conf import settings
from celery import Celery
from celery.schedules import crontab
import datetime
import pytz

CELERY_ENABLE_UTC = False
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'main.settings.common')


def get_now_fun():
    # PDT timezone for celery Beat
    return datetime.datetime.now(pytz.timezone('US/Pacific'))


app = Celery(
    'main',
    backend=os.environ.get('QUEUE_BACKEND'),
    broker=os.environ.get('QUEUE_BROKER_URL')
)

app.config_from_object('django.conf:settings', namespace='CELERY')
app.conf.broker_transport_options = {'visibility_timeout': 3600}  # 1 hour.

app.conf.beat_schedule = {
    'schedule-1': {
        'task': 'notification_request_remainder',
        'schedule': crontab(minute=0, hour=0, nowfun=get_now_fun),
        'args': (5, 6),
    },
    'schedule-2': {
        'task': 'notification_request_remainder',
        'schedule': crontab(minute=0, hour=0, nowfun=get_now_fun),
        'args': (6, 7),
    },
    'schedule-3': {
        'task': 'cancel_notification_no_response',
        'schedule': crontab(minute=0, hour='*/1', nowfun=get_now_fun),
    },
    'schedule-4': {
        'task': 'remove_unused_fcm_tokens',
        'schedule': crontab(minute=0, hour=0, day_of_week='monday', nowfun=get_now_fun),
    },
    'schedule-5': {
        'task': 'notify_admin_video_approvals',
        'schedule': crontab(minute=0, hour=0, nowfun=get_now_fun),
    },
    'schedule-6': {
        'task': 'create_monthly_payouts',
        'schedule': crontab(minute=0, hour=0, day_of_month=1, nowfun=get_now_fun),
    },
    'schedule-7': {
        'task': 'resend_failed_payouts',
        'schedule': crontab(minute=0, hour=0, day_of_month=6, nowfun=get_now_fun),
    },
    'schedule-8': {
        'task': 'resend_failed_payouts',
        'schedule': crontab(minute=1, hour=0, day_of_month=1, nowfun=get_now_fun),
    },
    'schedule-9': {
        'task': 'celebrity_request_notification',
        'schedule': crontab(minute=0, hour=0, nowfun=get_now_fun),
    },
    'schedule-10': {
        'task': 'setting_up_password',
        'schedule': crontab(minute=0, hour=0, nowfun=get_now_fun),
    },
    'schedule-11': {
        'task': 'trending_score_update',
        'schedule': crontab(minute=0, hour=0, day_of_month=8, nowfun=get_now_fun),
    },
    'schedule-12': {
        'task': 'delete_expired_profiles',
        'schedule': crontab(minute=0, hour=0, day_of_week='friday', nowfun=get_now_fun),
    },
    'schedule-13': {
        'task': 'deactivate_after_15_days',
        'schedule': crontab(minute=0, hour=0, nowfun=get_now_fun),
    },
    'schedule-14': {
        'task': 'tip_payments_payout_retry',
        'schedule': crontab(minute=0, hour=0, nowfun=get_now_fun),
    },

    # 'schedule-15': {
    #     'task': 'reprocess_pending_video_approval',
    #     'schedule': crontab(minute=0, hour=0),
    # },
    #'schedule-16': {
    #    'task': 'cancel_booking_on_seven_days_completion',
    #    'schedule': crontab(minute=0, hour=0),
    #},
}
app.conf.timezone = 'UTC'
app.conf.task_routes = {
    'job.tasks.generate_video_thumbnail': {'queue': 'videos'},
    'job.tasks.combine_video_clips': {'queue': 'videos'},
    'job.tasks.generate_reaction_videos': {'queue': 'videos'},
}

# This reads, e.g., CELERY_ACCEPT_CONTENT = ['json'] from settings.py:
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

app.conf.broker_transport_options = {
    'region': os.environ.get('QUEUE_REGION', 'us-east-1'),
    'queue_name_prefix':  os.environ.get('QUEUE_NAME_PREFIX', 'celery-'),
    'polling_interval':  int(os.environ.get('QUEUE_POLLING_INTERVAL', '60')),
}

app.conf.task_reject_on_worker_lost = True
app.conf.task_acks_late = True
app.worker_concurrency = 1
app.worker_prefetch_multiplier = 1
