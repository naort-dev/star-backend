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
from django.utils import timezone
import datetime


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

    try:
        celebrity = Celebrity.objects.get(user_id=celebrity_id)
    except Exception:
        return False

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
    receiver_email = admin_email

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
def welcome_email(user_id, not_recordable=None):
    from utilities.utils import sent_email, get_user_role_details

    model = apps.get_model('users', 'StargramzUser')
    try:
        user = model.objects.get(id=user_id)
    except model.DoesNotExist:
        return False

    template_box = {
        'R1001': 'welcome_fan',
        'R1002': 'welcome_celebrity',
        'R1003': 'welcome_fan',
        'R1004': 'welcome_group',
        'R1005': 'welcome_fan',
        'R1006': 'welcome_fan'
    }

    role = get_user_role_details(user)
    if role['is_complete']:
        subject = 'Welcome to Starsona!'
        template = template_box[role['role_code']]
        email = user.email
        ctx = {'auto_generation': True}

        return sent_email(email, subject, template, ctx)
    else:
        print('User profile is not complete.')


def representative_email(celebrity, representative):
    from utilities.utils import sent_email, encode_pk

    template = 'representative_email'
    subject = 'Welcome to Starsona'
    base_url = Config.objects.get(key='base_url').value
    representative_id = encode_pk(representative.id)
    ctx = {
        'representative_name': representative.first_name,
        'celebrity_name': celebrity.get_short_name(),
        'verify_link': "%srepresentative/email_verification/%s" % (base_url, representative_id)
    }

    return sent_email(representative.email, subject, template, ctx)


@app.task
def forgot_password_email(user_id):
    """
    The function will send a mail to the user with the reset link the reset link will redirect user to a password
    reset web page.
    :param user_id:
    :return:
    """
    from utilities.utils import sent_email, generate_branch_io_url
    from utilities.constants import BASE_URL, WEB_URL
    from .models import StargramzUser

    subject = 'Starsona Password Reset'
    template = 'forgot_password'
    try:
        reset_password_link = Config.objects.get(key='reset_password_link').value
        user = StargramzUser.objects.get(id=user_id)
        web_reset_url = "%s%s%s" % (WEB_URL, 'resetpassword?reset_id=', str(user.reset_id))
        ctx = {
            'username': user.first_name + ' ' + user.last_name,
            'reset_link': generate_branch_io_url(
                mob_url='reset/?reset_id=%s' % str(user.reset_id),
                title="Reset password for %s" % user.get_short_name(),
                desc="Reset password for %s" % user.get_short_name(),
                image_url='%smedia/web-images/starsona_logo.png' % BASE_URL,
                desktop_url=web_reset_url,
                canonical_url=reset_password_link + str(user.reset_id),
            )
        }
        sent_email(user.email, subject, template, ctx)
        return True
    except Exception:
        return False


@app.task
def change_file_bucket(file, file_name):
    import urllib.request
    from django.conf import settings
    from utilities.utils import get_pre_signed_get_url
    from job.tasks import check_file_exist_in_s3
    import boto3
    import os

    try:
        aws_production_bucket_name = Config.objects.get(key='aws_production_storage_bucket_name').value
        if file_name and check_file_exist_in_s3(file + file_name):
            picture_url = get_pre_signed_get_url(file_name, file)
            your_media_root = settings.MEDIA_ROOT + 'profile/'
            urllib.request.urlretrieve(picture_url, your_media_root + file_name)
            s3 = boto3.client('s3', aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
                              aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'))
            s3.upload_file(your_media_root + file_name, aws_production_bucket_name,
                           file + file_name)
            os.remove(your_media_root + file_name)
        return True
    except Exception as e:
        print(str(e))
        return False


@app.task
def send_star_approval_mail(user_id):
    from users.models import StargramzUser, VanityUrl
    from utilities.utils import sent_email, generate_branch_io_url, BASE_URL, WEB_URL
    try:
        user = StargramzUser.objects.get(id=user_id)
        vanity = VanityUrl.objects.get(user_id=user_id)
        template = 'star_approval'
        subject = 'Approve the star account'
        ctx = {
            'username': user.first_name + ' ' + user.last_name,
            'approval_link': generate_branch_io_url(
                mob_url='%sstar_approval?reset_id=%s&vanity_id=%s&migrated=true' % (WEB_URL, user.reset_id, vanity),
                title="Star approval for %s" % user.get_short_name(),
                desc="Star approval for %s" % user.get_short_name(),
                image_url='%smedia/web-images/starsona_logo.png' % BASE_URL,
                desktop_url='%sstar_approval?reset_id=%s&vanity_id=%s&migrated=true' % (WEB_URL, user.reset_id, vanity),
                canonical_url='%sstar_approval?reset_id=%s&vanity_id=%s&migrated=true' % (WEB_URL, user.reset_id, vanity)
            )
        }
        user.reset_id = None
        user.save()
        sent_email(user.email, subject, template, ctx)
        return True
    except Exception as e:
        print(str(e))
        return False


@app.task(name='trending_score_update')
def trending_score_update():
    from users.models import Celebrity, CelebrityFollow
    from stargramz.models import Stargramrequest, STATUS_TYPES
    celebrities = Celebrity.objects.filter(admin_approval=True, user__is_active=True)
    current_date = timezone.now()

    for celebrity in celebrities:
        # view count in last 60 days
        date_diff = (current_date - celebrity.created_date).days
        date_diff = date_diff if date_diff > 0 else 1
        views = celebrity.view_count
        if date_diff > 60:
            views = int((views/date_diff) * 60)
        else:
            views = views

        # follow count in last 60 days
        favorites = CelebrityFollow.objects.filter(
            celebrity_id=celebrity.user.id,
            created_date__gt=timezone.now()-datetime.timedelta(days=60)
        ).count()

        # purchase in the last 60 days
        purchase = Stargramrequest.objects.filter(
            celebrity=celebrity.user,
            created_date__gt=timezone.now() - datetime.timedelta(days=60)
        ).exclude(
            request_status=STATUS_TYPES.draft
        ).count()

        score = views + (5 * favorites) + (10 * purchase)
        celebrity.trending_star_score = score
        celebrity.save()
