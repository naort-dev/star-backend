from main.celery import app
from utilities.utils import sent_email, generate_branch_io_url
from utilities.constants import BASE_URL, WEB_URL
from users.models import StargramzUser, Celebrity, REMINDER_MAIL_COUNT, ProfileImage
from config.models import Config
import uuid
from django.utils import timezone
from datetime import datetime
import pytz
from django.apps import apps
from .utils import remove_files_from_s3, total_earnings_update, video_data_update, rating_data_update, tip_amount_update,\
    booking_count_update, biography_referral_update
from .models import CelebrityDashboard


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
        users = StargramzUser.objects.filter(temp_password=True, expiry_date__isnull=True)
        for user in users:
            date_diff = (datetime.now(pytz.UTC) - user.created_date).days
            template = ""
            if date_diff == int(first) and user.reminder_mail_count == REMINDER_MAIL_COUNT.first_mail:
                template = "setup_password"
                subject = "Good news! Then bad news. Then more good news!"
                user.reminder_mail_count = REMINDER_MAIL_COUNT.second_mail
            elif date_diff == int(second) and user.reminder_mail_count == REMINDER_MAIL_COUNT.second_mail:
                template = "setup_password_final"
                subject = "Your fans are waiting for you!"
                user.reminder_mail_count = REMINDER_MAIL_COUNT.no_mail
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
    sent_email(user.email, subject, template, ctx)


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


@app.task(name='delete_expired_profiles')
def delete_expired_profiles():
    users = StargramzUser.objects.filter(expiry_date__isnull=False)
    for user in users:
        if user.expiry_date < datetime.now(pytz.timezone('UTC')):
            print("Starsona account of %s is expired" % user.get_short_name())
            user.delete()


@app.task(name='deactivate_after_15_days')
def deactivate_after_15_days():
    users = StargramzUser.objects.filter(
        temp_password=True, expiry_date__isnull=True, reminder_mail_count=REMINDER_MAIL_COUNT.no_mail
    )
    mail_dates = Config.objects.get(key='password_reset_dates').value
    (first, second) = mail_dates.replace(' ', '').split(',')
    deactivate_date = int(second) + 1
    for user in users:
        date_diff = (datetime.now(pytz.UTC) - user.created_date).days
        if date_diff > deactivate_date:
            user.temp_password = False
            user.is_active = False
            user.save()


@app.task
def remove_existing_profile_video_from_s3(profile_video):
    file_path = Config.objects.get(key='authentication_videos').value
    file = file_path + profile_video
    remove_files_from_s3(file)


@app.task
def remove_profile_images_from_s3(images):
    file_path = Config.objects.get(key='profile_images').value
    for im in images:
        try:
            image = ProfileImage.objects.get(id=im)
            remove_files_from_s3(file_path + image.photo)
        except Exception as e:
            print(str(e))


@app.task
def celebrity_dashboard_update(user_id):
    current_date = datetime.now(pytz.UTC)
    dashboard, created = CelebrityDashboard.objects.get_or_create(user_id=user_id)
    if created:
        total_earnings_update(dashboard)  # total_earnings and pending_payments updates
        video_data_update(dashboard)  # video, reaction and comment count updates
        rating_data_update(dashboard)  # rating data updates
        tip_amount_update(dashboard)  # recent tip amount update
        booking_count_update(dashboard)  # booking count and its details update
        biography_referral_update(dashboard)  # updates the biography and referral check
        dashboard.last_updated_by_update_API = current_date
        dashboard.save()
    else:
        if dashboard.last_updated_by_update_API:
            diff_days = (current_date - dashboard.last_updated_by_update_API).days
            # the process only work if the last modified date if 24 hours back
            if diff_days >= 1:
                total_earnings_update(dashboard)  # total_earnings and pending_payments updates
                video_data_update(dashboard)  # video, reaction and comment count updates
                rating_data_update(dashboard)  # rating data updates
                tip_amount_update(dashboard)  # recent tip amount update
                booking_count_update(dashboard)  # booking count and its details update
                biography_referral_update(dashboard)  # updates the biography and referral check

                dashboard.last_updated_by_update_API = current_date
                dashboard.save()
