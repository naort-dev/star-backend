from main.celery import app
from utilities.utils import sent_email, generate_branch_io_url
from utilities.constants import BASE_URL, WEB_URL
from users.models import StargramzUser, Celebrity
from config.models import Config
import uuid
from django.utils import timezone
from datetime import datetime
import pytz
from django.apps import apps


@app.task(name='setting_up_password')
def setting_up_password():
    """
    The function will send a mail to the celebrity with the password setup link redirect celebrity to a password
    setup web page
    :return:
    """

    try:
        mail_dates = Config.objects.get(key='password_reset_dates').value  # the dates from the config is just for testing purpose
        (first, second) = mail_dates.replace(' ', '').split(',')
        users = StargramzUser.objects.filter(temp_password=True)
        for user in users:
            date_diff = (datetime.now(pytz.UTC) - user.created_date).days
            template = ""
            if date_diff == int(first):
                template = "setup_password"
                subject = "Good news! Then bad news. Then more good news!"
            elif date_diff == int(second):
                template = "setup_password_final"
                subject = "Your fans are waiting for you!"
                user.temp_password = False
                user.is_active = False
                user.save()
            if template:
                send_password_setup_mail(user, template, subject)
                print("setup mail send to %s" % user.get_short_name())
        return True
    except Exception as e:
        print(str(e))
        return False


def send_password_setup_mail(user, template, subject, ctx={}):
    user.reset_id = uuid.uuid4()
    user.reset_generate_time = timezone.now()
    user.save()
    reset_password_link = Config.objects.get(key='reset_password_link').value
    web_reset_url = "%s%s%s" % (WEB_URL, 'resetpassword?reset_id=', str(user.reset_id))
    sender_email = Config.objects.get(key='sender_email').value
    ctx.update(
        {
            'username': user.get_short_name(),
            'reset_link': generate_branch_io_url(
                mob_url='reset/?reset_id=%s' % str(user.reset_id),
                title="Reset password for %s" % user.get_short_name(),
                desc="Reset password for %s" % user.get_short_name(),
                image_url='%smedia/web-images/starsona_logo.png' % BASE_URL,
                desktop_url=web_reset_url,
                canonical_url=reset_password_link + str(user.reset_id),
            ),
            'mail': sender_email,
            'subject': 'Questions'
        }
    )
    sent_email('vidyav@qburst.com', subject, template, ctx)


@app.task
def welcome_email_version_2(user_id, not_recordable):
    from utilities.utils import sent_email

    model = apps.get_model('users', 'StargramzUser')
    try:
        user = model.objects.get(id=user_id)
        celebrity = Celebrity.objects.get(user_id=user.id)
    except model.DoesNotExist:
        return False
    subject = 'Welcome to Starsona!'
    email = user.email
    ctx = {
        'celebrity_name': user.get_short_name()
    }

    if user.temp_password:
        if celebrity.profile_video:
            template = 'welcome_mail_version_2/welcome_celebrity_email'
        elif not_recordable:
            template = 'welcome_mail_version_2/welcome_celebrity_non_recordable'
            ctx.update({'team_mail': Config.objects.get(key='team_email').value})
        else:
            template = 'welcome_mail_version_2/welcome_celebrity_no_profile_video'
        send_password_setup_mail(user, template, subject, ctx=ctx)
        return True
    else:
        template = 'welcome_mail_version_2/welcome_celebrity_social'

    return sent_email(email, subject, template, ctx)
