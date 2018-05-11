from main.celery import app
from utilities.konstants import NOTIFICATION_TYPES
from django.db.models import Q
from .constants import ALERT_FAN_NOTIFICATION_TITLE, ALERT_FAN_NOTIFICATION_BODY
from utilities.konstants import ROLES
from django.template.loader import get_template
from config.models import Config
from django.db.models import F
from django.utils.safestring import mark_safe
from django.apps import apps


@app.task(name='update_remaining_limit')
def change_remaining_limit():
    from .models import Celebrity
    print('Remaining Limit updated to weekly Limit')
    celebrities = Celebrity.objects.all()
    celebrities.update(remaining_limit=F('weekly_limits'))
    for celebrity in celebrities:
        celebrity.save()
    return True


@app.task
def alert_fans_celebrity_available(celebrity_id):
    from notification.tasks import send_notification
    from utilities.utils import SendMail
    from .models import CelebrityAvailableAlert

    celebrities = CelebrityAvailableAlert.objects.filter(Q(celebrity_id=celebrity_id) &
                                                         Q(notification_send=False))
    for celebrity in celebrities:
        data = {'id': celebrity.celebrity.id, 'type': NOTIFICATION_TYPES.alert_fan_celebrity_available,
                'role': ROLES.fan}
        send_notification.delay(celebrity.fan.id,
                                ALERT_FAN_NOTIFICATION_TITLE,
                                ALERT_FAN_NOTIFICATION_BODY % (celebrity.celebrity.get_short_name()),
                                data)
        subject = '%s is now available' % celebrity.celebrity.get_short_name()

        sender_email = Config.objects.get(key='sender_email').value
        base_url = Config.objects.get(key='base_url').value
        ctx = {
            'base_url': base_url,
            'celebrity_name': celebrity.celebrity.get_short_name(),
            'fan_name': celebrity.fan.get_short_name(),
        }

        html_template = get_template('../templates/emails/alert_me.html')
        html_content = html_template.render(ctx)

        try:
            SendMail(subject, html_content, sender_email=sender_email, to=celebrity.fan.email)
        except Exception as e:
            print(str(e))
    celebrities.update(notification_send=True)


@app.task
def alert_admin_celebrity_updates(celebrity_id, type_id):
    from utilities.utils import SendMail
    from .models import Celebrity

    celebrity = Celebrity.objects.get(user_id=celebrity_id)
    sender_email = Config.objects.get(key='sender_email').value
    admin_email = Config.objects.get(key='admin_email').value
    base_url = Config.objects.get(key='base_url').value
    profile_url = '%s/admin/users/celebrityuser/%d/change/' % (base_url, celebrity_id)
    email_content = {'subject_1': '%s has just registered' % celebrity.user.get_short_name(),
                     'body_1': '%s has completed the registration process and is now pending approval.<br/>'
                               '<p style="text-align:center"><a href="%s" class="button">Review registration</a></p>'
                               '<br/><br/>Thanks!' % (celebrity.user.get_short_name(), profile_url),
                     'subject_2': 'Celebrity account updates',
                     'body_2': '%s has updated his account' % celebrity.user.get_short_name(),
                     'subject_3': '%s is now live' % celebrity.user.get_short_name(),
                     'body_3': 'Starsona admin has reviewed and approved the'
                               ' profile for %s. They are now searchable by fans.<br/><br/>'
                               'Thanks,<br/>The Starsona Team' % celebrity.user.get_short_name(),
                     }
    subject = email_content['subject_%s' % type_id]
    receiver_email = celebrity.user.email if type_id == 3 else admin_email

    ctx = {
        'base_url': base_url,
        'body': mark_safe(email_content['body_%s' % type_id])
    }

    html_template = get_template('../templates/emails/celebrity_update.html')
    html_content = html_template.render(ctx)

    try:
        SendMail(subject, html_content, sender_email=sender_email, to=receiver_email)
    except Exception as e:
        print(str(e))


@app.task
def report_abuse_notify(user_id, request_id):
    from utilities.utils import SendMail
    from .models import StargramzUser

    user = StargramzUser.objects.get(id=user_id)
    subject = 'Booking Reported Abuse'
    sender_email = Config.objects.get(key='sender_email').value
    admin_email = Config.objects.get(key='admin_email').value
    base_url = Config.objects.get(key='base_url').value
    ctx = {
        'base_url': base_url,
        'reporter_name': user.get_short_name(),
        'booking_id': request_id
    }

    html_template = get_template('../templates/emails/report_abuse.html')
    html_content = html_template.render(ctx)

    try:
        SendMail(subject, html_content, sender_email=sender_email, to=admin_email)
        print('Abuse reported Notified.')
    except Exception as e:
        print(str(e))


@app.task
def welcome_email(user_id):
    from utilities.utils import sent_email, get_user_role_details

    model = apps.get_model('users', 'StargramzUser')
    try:
        user = model.objects.get(id=user_id)
    except model.DoesNotExist:
        pass

    role = get_user_role_details(user)
    if role['is_complete']:
        subject = 'Welcome to Starsona!'
        template = 'welcome_fan' if role['role_code'] == 'R1001' else 'welcome_celebrity'
        email = user.email
        ctx = {'auto_generation': True}

        return sent_email(email, subject, template, ctx)
    else:
        print('User profile is not complete.')
