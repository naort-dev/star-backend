import boto3
from django.template import loader
from django.conf import settings
from users.models import UserRoleMapping
from utilities.konstants import ROLES
from utilities.mixins import ResponseViewMixin
import string
import random
import requests
import json
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext as _
from django.core.mail import send_mail
from .constants import PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH, BASE_URL
from rest_framework import serializers
from django.http import HttpResponse
from django.utils.encoding import smart_str
import os
from main.settings.common import MEDIA_ROOT
from django.utils.html import format_html_join
from django.utils.safestring import mark_safe
from config.models import Config
from users.models import ProfileImage, Celebrity, SettingsNotifications, GroupAccount, StargramzUser, \
    CelebrityGroupAccount, Representative
import datetime
import re
from tempfile import gettempdir
from fcm_django.models import FCMDevice
from django.db.models import Q
from django.template.loader import get_template
import urllib.request
from stargramz.models import StargramVideo
from hashids import Hashids
hashids = Hashids(min_length=8)


def get_user_role_details(user):
    mappings = UserRoleMapping.objects.filter(user=user)
    role = {}
    if mappings:
        mapping = mappings[0]
        role = {
            'id': mapping.id,
            'role_code': mapping.role.code,
            'role_name': mapping.role.role_display(),
            'is_complete': mapping.is_complete
        }
    return role


def check_user_role(user, role):
    mappings = UserRoleMapping.objects.filter(Q(user=user) | Q(user_id=user))
    if mappings:
        mapping = mappings[0]
        if mapping.role.code == role:
            return True
    return False


def check_if_valid_role(role):
    is_valid = False
    for item in ROLES.choices():
        if role == item[0]:
            is_valid = True
    return is_valid


def get_pre_signed_post_url(filename, expires, expiry=3600, private=False):
    """
        Get Pre Signed url to upload a file.
    """
    s3 = boto3.client('s3', aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
                      aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'))

    if private:
        acl = 'private'
    else:
        acl = 'public-read'
    fields = {
        'success_action_status': "201",
        'acl': acl,
        'Access-Control-Allow-Origin': '*',
        'Expires': expires
    }
    conditions = [
        {
            'success_action_status': "201",
        },
        {
            'acl': acl
        },
        {
            'Access-Control-Allow-Origin': '*'
        },
        # {
        #     'Expires': expires
        # },
        # ["starts-with", "$Content-Type", ""]
        # Means that Content-type starts with any value
    ]

    post = s3.generate_presigned_post(
        Bucket=os.environ.get('AWS_STORAGE_BUCKET_NAME'),
        Key=filename,
        Fields=fields,
        Conditions=conditions,
        ExpiresIn=expiry
    )
    return post


def get_pre_signed_get_url(filename, folder, expires_in=3600):
    """
        Get pre signed url to download a file.
    """
    s3 = boto3.client(
        's3',
        aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
    )
    url = s3.generate_presigned_url(
        ClientMethod='get_object',
        Params={
            'Bucket': os.environ.get('AWS_STORAGE_BUCKET_NAME'),
            'Key': folder+filename
        },
        ExpiresIn=expires_in
    )
    return url


def get_s3_public_url(filename, folder):
    """
    Get the url for a public file in s3
    :param folder:
    :param filename:
    :return: formatted S3 URL
    """
    s3 = boto3.client(
        's3',
        aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY')
    )
    return '{}/{}/{}'.format(s3.meta.endpoint_url, os.environ.get('AWS_STORAGE_BUCKET_NAME'), folder + filename)


def get_bucket_url():
    """
    Get the S3 bucket URL
    :return:
    """
    s3 = boto3.client(
        's3',
        aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY')
    )

    return '{}/{}'.format(s3.meta.endpoint_url, os.environ.get('AWS_STORAGE_BUCKET_NAME'))


def upload_image_s3(path, filename):
    """
        Upload the file to s3 server
    """
    s3 = boto3.client('s3', aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
                      aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'))
    s3.upload_file(path, os.environ.get('AWS_STORAGE_BUCKET_NAME'), filename)


def generate_password(size=8, chars=string.ascii_uppercase + string.ascii_lowercase + string.digits):
        return ''.join(random.choice(chars) for _ in range(size))


def SendMail(subject, html_content, **kwargs):
    try:
        text_content = ''
        send_mail(
            subject,
            text_content,
            kwargs.get('sender_email'),
            [kwargs.get('to')],
            fail_silently=False,
            html_message=html_content
        )
        return True
    except Exception as e:
        return False


class CustomPasswordValidator(object):

    def __init__(self, min_length=1):
        self.min_length = min_length

    def validate(self, password, user=None):
        password = password.replace(" ", "")
        if re.match("^[a-zA-Z0-9]*$", password):
            raise ValidationError(_(
                'Password must contain at least %(min_length)d special character.') % {'min_length': self.min_length})
        if len(password) > PASSWORD_MAX_LENGTH:
            raise ValidationError(_(
                'Password must contain at most %(max_length)d digit.') % {'max_length': PASSWORD_MAX_LENGTH})
        if len(password) < PASSWORD_MIN_LENGTH:
            raise ValidationError(_(
                'Password must contain at least %(max_length)d digit.') % {'max_length': PASSWORD_MIN_LENGTH})
        # if not any(char.isdigit() for char in password):
        #     raise ValidationError(_(
        #         'Password must contain at least %(min_length)d digit.') % {'min_length': self.min_length})
        # if not any(char.isalpha() for char in password):
        #     raise ValidationError(_(
        #         'Password must contain at least %(min_length)d letter.') % {'min_length': self.min_length})

    def get_help_text(self):
        return ""


def removefromdict(data, keys):
    for key in keys:
        data.pop(key)
    return data


class CustomModelSerializer(serializers.ModelSerializer):

    def __init__(self, *args, **kwargs):
        # Don't pass the 'fields' arg up to the superclass
        fields = kwargs.pop('fields', None)
        # Instantiate the superclass normally
        super(CustomModelSerializer, self).__init__(*args, **kwargs)
        if fields is not None:
            # Drop any fields that are not specified in the `fields` argument.
            allowed = set(fields)
            existing = set(self.fields.keys())
            for field_name in existing - allowed:
                self.fields.pop(field_name)


def download_file(request, path, content_type="application/pkcs7-mime"):

    file_path = os.path.join(MEDIA_ROOT, path)
    if os.path.exists(file_path):
        with open(file_path, 'rb') as fh:
            response = HttpResponse(fh.read(), content_type=content_type)
            response['Content-Disposition'] = 'inline; filename=' + os.path.basename(file_path)
            response['X-Sendfile'] = smart_str(file_path)
            return response


def download_video(request, id):
    """
        Download the Video
    """
    try:
        video_id = hashids.decode(id)[0]
    except Exception as e:
        return HttpResponse(content_type='video/mp4')

    video_download = video_url = None
    try:
        video = StargramVideo.objects.get(
            id=video_id,
        )
        S3_path = Config.objects.get(key='stargram_videos').value
        video_url = get_pre_signed_get_url(video.video, S3_path)
        file_name = "/%s-%d" % (
            re.sub('[^A-Za-z0-9]+', '-', video.stragramz_request.booking_title).lower(),
            video.stragramz_request_id
        )
        video_download = gettempdir() + file_name+'-starsona.mp4'
    except Exception as e:
        return HttpResponse(content_type='video/mp4')

    try:
        # Downloading video from s3
        urllib.request.urlretrieve(video_url, video_download)
    except Exception as e:
        return HttpResponse(content_type='video/mp4')
    try:
        if os.path.exists(video_download):
            with open(video_download, 'rb') as fh:
                response = HttpResponse(fh.read(), content_type='video/mp4')
                response['Content-Disposition'] = 'attachment; filename=' + os.path.basename(video_download)
                response['X-Sendfile'] = smart_str(video_download)
                return response
    except Exception as e:
        return HttpResponse(content_type='video/mp4')


def get_profile_images(request, user_id, img_count=1, **kwargs):
    image_list = {}

    avatar = kwargs.pop('avatar_id', None)

    try:
        images = ProfileImage.objects.filter(user=user_id, status=1)
        config = Config.objects.get(key='profile_images')
        image_list = {obj.id: get_pre_signed_get_url(obj.photo, config.value) for obj in images}
    except Exception:
        pass
    return loader.render_to_string(
        template_name='admin/images-list.html',
        context={'images': image_list, 'id': user_id, 'img_count': img_count, 'avatar_id': avatar},
        request=None
    )


def get_featured_image(request, user_id, featured_image):
    """
        Get the featured image for the user and update
    """
    try:
        images = ProfileImage.objects.filter(user=user_id, id=featured_image)
        config = Config.objects.get(key='profile_images')
        image_list = {obj.id: get_pre_signed_get_url(obj.photo, config.value) for obj in images}
    except Exception:
        pass
    return loader.render_to_string(
        template_name='admin/featured_images.html',
        context={'images': image_list, 'id': user_id, 'img_count': 5, 'avatar_id': None},
        request=None
    )


def get_profile_video(id):
    video = Celebrity.objects.filter(user_id=id)
    config = Config.objects.get(key='authentication_videos')
    return format_html_join(
        '',
        '<video width="320" height="240" controls><source src="{}" type="video/mp4">'
        'Your browser does not support the video tag.</video>',
        ((get_pre_signed_get_url(obj.profile_video, config.value),) for obj in video),
    ) or mark_safe("<span>No Profile video available.</span>")


def get_audio(file_name):

    audio_html = '<audio controls preload="none" style="width:480px;">' \
                 '<source src="%s" type="audio/mp4" />' \
                 '<p>Your browser does not support HTML5 audio.</p></audio>'
    audio_file = get_pre_signed_get_url(file_name, '') if file_name else ''

    return mark_safe((audio_html % audio_file) if file_name else '<span>No audio available.</span>')


def datetime_range(start_date, end_date):
    """
        To covert date field to datetime field
    """
    from_date_time = datetime.datetime.combine(start_date, datetime.time.min)
    to_date_time = datetime.datetime.combine(end_date, datetime.time.max)

    return dict(from_datetime=from_date_time, to_datetime=to_date_time)


def change_fcm_device_status(user, status, registration_id):
    """
        To change the device FCM status
    """
    try:
        user_token = FCMDevice.objects.get(user=user, registration_id=registration_id)
        user_token.active = status
        user_token.save()
        if status:
            FCMDevice.objects.filter(registration_id=registration_id).exclude(user=user).update(active=False)
    except FCMDevice.DoesNotExist:
        pass


def verify_user_for_notifications(user_id, field, **kwargs):
    """
        To check if user is accepting notifications and email
    """
    send_message = False
    role = kwargs.pop('role', None)
    try:
        notification_settings = SettingsNotifications.objects.get(user_id=user_id)
    except Exception:
        notification_settings = None
    if notification_settings:
        if role:
            if check_user_role(user_id, role):
                send_message = getattr(notification_settings, field)
        else:
            send_message = getattr(notification_settings, field)
    return send_message


def check_celebrity_profile_exist(user):
    try:
        Celebrity.objects.values_list('id', flat=True).get(Q(user=user) | Q(user_id=user))
    except Celebrity.DoesNotExist:
        return False
    return True


def check_group_account_profile_exist(user):
    try:
        result = GroupAccount.objects.get(Q(user=user) | Q(user_id=user))
        return True, result
    except GroupAccount.DoesNotExist:
        return False, None


def is_following_group_account(user, account):
    from users.serializer import CelebrityGroupAccountSerializer
    """
    Check wheather the celebrity following the group account
    :param user:
    :param account:
    :return: Boolean
    """
    try:
        group_approval = CelebrityGroupAccount.objects.get(user_id=user, account=account)
        return True, CelebrityGroupAccountSerializer(group_approval).data
    except CelebrityGroupAccount.DoesNotExist:
        return False, {}


def sent_email(to_email, subject, template, ctx):
    """
        Sent email
    """
    sender_email = Config.objects.get(key='sender_email').value
    ctx.update({'base_url': BASE_URL})

    html_template = get_template('../templates/emails/%s.html' % template)
    html_content = html_template.render(ctx)

    try:
        return SendMail(subject, html_content, sender_email=sender_email, to=to_email)
    except Exception as e:
        print(str(e))


def generate_branch_io_url(mob_url='', title='', desc='', image_url='', desktop_url='', canonical_url=''):
    """
        Generate url to track via branch io

        :param mob_url: URL used to navigate to profile in Mobile app
        :param title: Title of the page for Social media sharing
        :param desc: Description of page for Social media sharing
        :param image_url: Image URL of the page for Social media sharing
        :param desktop_url: Desktop URL top navigate for desktop clients
        :param canonical_url: Canonical is actual web url
        :return: URL
    """
    headers = {'Content-Type': 'application/json'}
    links = mob_url.split("/") if len(mob_url) > 1 else ''
    payload = {
        'branch_key': os.environ.get('BRANCH_IO_KEY'),
        'data': {
            '$deeplink_path': mob_url,
            '$canonical_identifier': mob_url,
            '$canonical_url': canonical_url if canonical_url else desktop_url,
            '$ios_deeplink_path': mob_url,
            '$android_deeplink_path': mob_url,
            '$og_title': title,
            '$og_description': desc,
            '$fallback_url': desktop_url,
            '$og_image_url': image_url,
            '$desktop_url': desktop_url,
            'nav_to': links[0] if links[0] else '',

        }
    }

    url = 'https://api.branch.io/v1/url'
    try:
        data = json.dumps(payload)
        response = requests.post(url=url, data=data, headers=headers)
        return_data = response.json()
        return return_data['url']
    except Exception:
        return desktop_url


def encode_pk(pk):
    try:
        return hashids.encode(pk)
    except Exception as e:
        return ResponseViewMixin.jp_error_response('HTTP_400_BAD_REQUEST', 'EXCEPTION', str(e))


def decode_pk(pk):
    try:
        return hashids.decode(pk)[0]
    except Exception as e:
        return ResponseViewMixin.jp_error_response('HTTP_400_BAD_REQUEST', 'EXCEPTION', str(e))


def get_user_id(slug_name):
    """
    Get the user id from vanity url name
    :param slug_name:
    :return: user id
    """
    try:
        user_id = StargramzUser.objects.get(vanity_urls__name=slug_name)
        return user_id
    except Exception as e:
        raise str(e)


def representative_notify(celebrity, fan, occasion):
    """
    Send a Notifying email to representatives of the celebrity about the new registered booking
    :param celebrity:
    :param fan:
    :param occasion:
    :return: True
    """
    representatives = Representative.objects.filter(celebrity=celebrity, email_verified=True)
    if representatives:
        for representative in representatives:
            if representative.email:
                ctx = {
                    'celebrity_name': celebrity.get_short_name(),
                    'fan_name': fan.get_short_name(),
                    'occasion': occasion,
                    'representative_name': representative.first_name
                }
                sent_email(representative.email, 'Starsona Request Notification', 'representative_notify', ctx)
    return True


def group_notify(celebrity, account):
    """
        Send a notification mail to the group when a celebrity supports it
    :param celebrity:
    :param account:
    :return:
    """
    account = get_user_id(account)
    ctx = {
        'account_name': account.get_short_name(),
        'celebrity_name': celebrity.get_short_name(),
        'redirect_link': generate_branch_io_url(
            desktop_url='%ssettings' % BASE_URL,
            mob_url='%ssettings' % BASE_URL,
            image_url='%smedia/web-images/starsona_logo.png' % BASE_URL,
            title='Group Joining Request',
            desc='Group Joining Request',
        )
    }
    sent_email(account.email, 'Group Invite Request', 'group_join_notify', ctx)
    return True


def invite_celebrity_notify(account, celebrity):
    """
        Send a notification mail to the celebrity when group invites that celebrity
    :param account:
    :param celebrity:
    :return:
    """
    ctx = {
        'account_name': account.get_short_name(),
        'celebrity_name': celebrity.get_short_name(),
        'redirect_link': generate_branch_io_url(
            desktop_url='%ssettings' % BASE_URL,
            mob_url='%ssettings' % BASE_URL,
            image_url='%smedia/web-images/starsona_logo.png' % BASE_URL,
            title='Group Invite',
            desc='Group Invite',
        ),
        'joining_link': '%ssettings' % BASE_URL
    }
    sent_email(celebrity.email, 'Group Invite', 'group_invite_notify', ctx)
    return True
