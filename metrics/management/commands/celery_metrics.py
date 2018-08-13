import time
from django.core.management import BaseCommand
import celery
import boto3
from datetime import datetime
import os

client = boto3.client('cloudwatch')

class Command(BaseCommand):
    help = "Emits celery metrics"
    def handle(self, *args, **options):
        queue_name = os.environ.get('QUEUE_NAME_PREFIX') + 'celery'
        interval = 60
        while True:
            time.sleep(interval)
            active, scheduled, reserved = _count()
            current_time = datetime.utcnow()
            print('Counts: %d %d %d' % (active, scheduled, reserved))
            client.put_metric_data(
                Namespace='Celery',
                MetricData=[
                    {
                        'MetricName': 'ActiveCount',
                        'Dimensions': [
                            {
                                'Name': 'QueueName',
                                'Value': queue_name
                            },
                        ],
                        'Timestamp': current_time,
                        'Value': active,
                        'Unit': 'Count',
                        'StorageResolution': interval
                    },
                    {
                        'MetricName': 'ScheduledCount',
                        'Dimensions': [
                            {
                                'Name': 'QueueName',
                                'Value': queue_name
                            },
                        ],
                        'Timestamp': current_time,
                        'Value': scheduled,
                        'Unit': 'Count',
                        'StorageResolution': interval
                    },
                    {
                        'MetricName': 'ReservedCount',
                        'Dimensions': [
                            {
                                'Name': 'QueueName',
                                'Value': queue_name
                            },
                        ],
                        'Timestamp': current_time,
                        'Value': reserved,
                        'Unit': 'Count',
                        'StorageResolution': interval
                    },
                    {
                        'MetricName': 'TotalCount',
                        'Dimensions': [
                            {
                                'Name': 'QueueName',
                                'Value': queue_name
                            },
                        ],
                        'Timestamp': current_time,
                        'Value': active + scheduled + reserved,
                        'Unit': 'Count',
                        'StorageResolution': interval
                    },
                ]
            )

def ccount(d):
    k = next(iter(d.keys()))
    return len(d[k])

def _count():
    cinspect = celery.current_app.control.inspect()
    return ccount(cinspect.active()), ccount(cinspect.scheduled()), ccount(cinspect.reserved())

