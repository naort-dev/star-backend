from main.celery import app
from fcm_django.models import FCMDevice
from .constants import PENDING_REQUEST_KEY, ROLE, COMPLETED_FAN_UNSEEN_KEY
from utilities.utils import verify_user_for_notifications
from users.models import StargramzUser
from django.db.models import F


@app.task
def send_notification(user_id, title=None, body=None, data=None, icon=None, **kwargs):
    """
        Send Push Notification to Device/Web
    """
    try:
        id = type = pending_request_count = role = completed_fan_unseen_count = None
        send_message = True
        notification_field = kwargs.pop('field', None)
        user = StargramzUser.objects.get(id=user_id)
        if notification_field:
            send_message = verify_user_for_notifications(user_id, notification_field)
        if send_message:
            devices = FCMDevice.objects.filter(user_id=user_id, active=True)
            if data:
                id = data.get('id', None)
                type = data.get('type', None)
                pending_request_count = data.get('pending_request_count', None)
                completed_fan_unseen_count = data.get('completed_fan_unseen_count', None)
                role = data.get('role', None)
            fcm_data = create_fcm_data(title, body, type, id, icon,
                                       pending_request_count=pending_request_count,
                                       completed_fan_unseen_count=completed_fan_unseen_count,
                                       role=role)
            print(data)
            user.notification_badge_count = F('notification_badge_count') + 1
            user.save()
            user.refresh_from_db()
            status = devices.send_message(title=title, body=body, data=fcm_data,
                                          badge=user.notification_badge_count)
            print('Message has been sent:', status)
    except Exception as e:
        print(str(e))


def create_fcm_data(title=None, body=None, type=None, id=None, icon=None, **kwargs):
    """
        To generate an fcm_data
    """
    data = {}
    kwargs_dict = {}
    keys = ["title", "body", "type", "id", "icon"]
    values = [title, body, type, id, icon]
    kwargs_dict[PENDING_REQUEST_KEY] = kwargs.pop(PENDING_REQUEST_KEY, None)
    kwargs_dict[ROLE] = kwargs.pop(ROLE, None)
    kwargs_dict[COMPLETED_FAN_UNSEEN_KEY] = kwargs.pop(COMPLETED_FAN_UNSEEN_KEY, None)
    for key, value in kwargs_dict.items():
        if value:
            keys.append(key)
            values.append(value)
    for key, value in zip(keys, values):
        if value:
            data[key] = value
    return data


@app.task(name='remove_unused_fcm_tokens')
def remove_unused_fcm_tokens():
    """
        Remove unused fcm device tokens with status False
    """
    FCMDevice.objects.filter(active=False).delete()
