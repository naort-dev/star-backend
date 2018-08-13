from __future__ import absolute_import, unicode_literals
import os
from django.conf import settings
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'main.settings.common')

app = Celery(
    'main',
    backend=os.environ.get('QUEUE_BACKEND'),
    broker=os.environ.get('QUEUE_BROKER_URL')
)

app.config_from_object('django.conf:settings', namespace='CELERY')
app.conf.beat_schedule = {
    'schedule-1': {
        'task': 'update_remaining_limit',
        'schedule': crontab(minute=0, hour=0, day_of_week='monday'),
    },
    'schedule-2': {
        'task': 'notification_request_remainder',
        'schedule': crontab(minute=0, hour=0),
        'args': (5, 6),
    },
    'schedule-3': {
        'task': 'notification_request_remainder',
        'schedule': crontab(minute=0, hour=0),
        'args': (6, 7),
    },
    'schedule-4': {
        'task': 'cancel_notification_no_response',
        'schedule': crontab(minute=0, hour=0),
    },
    'schedule-5': {
        'task': 'remove_unused_fcm_tokens',
        'schedule': crontab(minute=0, hour=0, day_of_week='monday'),
    },
    'schedule-6': {
        'task': 'notify_admin_video_approvals',
        'schedule': crontab(minute=0, hour=0),
    },
    'schedule-7': {
        'task': 'create_monthly_payouts',
        'schedule': crontab(minute=0, hour=0, day_of_month=1),
    },
    'schedule-8': {
        'task': 'resend_failed_payouts',
        'schedule': crontab(minute=0, hour=0, day_of_month=6),
    },
    'schedule-9': {
        'task': 'resend_failed_payouts',
        'schedule': crontab(minute=1, hour=0, day_of_month=1),
    },
}
app.conf.timezone = 'UTC'
app.conf.task_routes = {
    'job.tasks.generate_video_thumbnail': {'queue': 'videos'},
    'job.tasks.combine_video_clips': {'queue': 'videos'}
}

# This reads, e.g., CELERY_ACCEPT_CONTENT = ['json'] from settings.py:
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

app.conf.broker_transport_options = {
    'region': os.environ.get('QUEUE_REGION', 'us-east-1'),
    'queue_name_prefix':  os.environ.get('QUEUE_NAME_PREFIX', 'celery-'),
    'polling_interval':  int(os.environ.get('QUEUE_POLLING_INTERVAL', '60')),
}

