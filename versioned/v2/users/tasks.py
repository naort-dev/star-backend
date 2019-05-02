from main.celery import app
from utilities.utils import sent_email, generate_branch_io_url
from utilities.constants import BASE_URL, WEB_URL
from users.models import StargramzUser
from config.models import Config
import uuid
from django.utils import timezone
from datetime import datetime
import pytz


@app.task
def setting_up_password():
    """
    The function will send a mail to the celebrity with the password setup link redirect celebrity to a password
    setup web page
    :return:
    """

    try:
        users = StargramzUser.objects.filter(temp_password=True)
        for user in users:
            date_diff = (datetime.now(pytz.UTC) - user.created_date).days
            if date_diff == 7:
                send_password_setup_mail(user, 'in 7 days')
            elif date_diff == 14:
                send_password_setup_mail(user, 'Today')
                user.temp_password = False
                user.save()
        return True
    except Exception as e:
        print(str(e))
        return False

def send_password_setup_mail(user, message):
    subject = 'Starsona Password Setup'
    template = 'setup_password'
    user.reset_id = uuid.uuid4()
    user.reset_generate_time = timezone.now()
    user.save()
    reset_password_link = Config.objects.get(key='reset_password_link').value
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
        ),
        'message': message
    }
    sent_email(user.email, subject, template, ctx)
