from moviepy.editor import *
from moviepy import *
from moviepy.video.fx.resize import resize
from moviepy.video.compositing.transitions import slide_in
from stargramz.models import Stargramrequest, StargramVideo, STATUS_TYPES, Occasion, VIDEO_STATUS, Reaction, REQUEST_TYPES
from payments.models import StarsonaTransaction, PaymentPayout, TRANSACTION_STATUS, PAYOUT_STATUS, PAYMENT_TYPES
import stripe
from stargramz.constants import *
from payments.constants import SECRET_KEY
from main.celery import app
from botocore.exceptions import ClientError
import os
from PIL import Image, ExifTags, ImageOps
from django.conf import settings
from django.template.loader import get_template
from users.models import ProfileImage, Celebrity, StargramzUser, Campaign, CelebrityGroupAccount, SettingsNotifications
from config.models import Config
from config.constants import *
from utilities.utils import get_pre_signed_get_url, upload_image_s3, SendMail, verify_user_for_notifications,\
    generate_branch_io_url, sent_email, representative_notify, get_bucket_url, encode_pk
import urllib.request
from datetime import datetime, timedelta
import imageio
import time, json
import re
from contextlib import contextmanager
from django.core.cache import cache
from hashids import Hashids
from utilities.constants import BASE_URL
from utilities.konstants import NOTIFICATION_TYPES, ROLES
from django.db.models import Sum
from twilio.rest import Client
from django_slack import slack_message
from payments.utils import in_app_price_reduction, has_ambassador
imageio.plugins.ffmpeg.download()

hashids = Hashids(min_length=8)
size = (300, 300)
video_thumb_size = (400, 400)


from celery import signals
import boto3
import sys

tasks_active = 0
last_task_complete = time.time()
max_idle = int(os.environ.get('MAX_IDLE', 0))
min_count = int(os.environ.get('MIN_COUNT', 1))

@signals.heartbeat_sent.connect
def heartbeat_sent(sender, **kwargs):
    global tasks_active
    global last_task_complete
    global max_idle
    global min_count
    if tasks_active > 0 or max_idle <= 0:
        return

    idle = time.time() - last_task_complete
    if idle < max_idle:
        return

    last_task_complete = time.time()
    ecs_cluster = os.environ.get('ECS_CLUSTER')
    ecs_service = os.environ.get('ECS_SERVICE')
    if not (ecs_cluster and ecs_service):
        return

    client = boto3.client('ecs')
    service = client.describe_services(
        cluster=ecs_cluster,
        services=[ecs_service])['services'][0]

    desiredCount = service['desiredCount']

    if desiredCount > min_count:
        print('idle for %f sec, shutting down...' % idle)
        client.update_service(
            cluster=ecs_cluster,
            service=ecs_service,
            desiredCount=desiredCount - 1)
        sys.exit(0)

    
@signals.task_prerun.connect
def task_prerun(task_id, task, args, **kwargs):
    global tasks_active
    tasks_active += 1

@signals.task_postrun.connect
def task_postrun(task_id, task, args, **kwargs):
    global tasks_active
    global last_task_complete
    tasks_active -= 1
    last_task_complete = time.time()
    

def video_rotation(video):
    """
        Rotate the video based on orientation
    """
    rotation = video.rotation
    if rotation == 90:  # If video is in portrait
        video = vfx.rotate(video, -90)
    elif rotation == 270:  # Moviepy can only cope with 90, -90, and 180 degree turns
        video = vfx.rotate(video, 90)  # Moviepy can only cope with 90, -90, and 180 degree turns
    elif rotation == 180:
        video = vfx.rotate(video, 180)
    return video


@app.task
def generate_thumbnail():
    """
        Generate the thumbnail for the profile photos and upload to s3
    """

    images = ProfileImage.objects.filter(thumbnail__isnull=True)
    config = Config.objects.get(key='profile_images')
    your_media_root = settings.MEDIA_ROOT + 'thumbnails/'
    s3folder = config.value

    for image in images:
        img_url = get_pre_signed_get_url(image.photo, s3folder)
        image_original = your_media_root+image.photo
        print("image: "+image.photo)
        if check_file_exist_in_s3(s3folder+image.photo) is not False:
            try:
                # Downloading the image from s3
                urllib.request.urlretrieve(img_url, image_original)

                thumbnail_name = "thumbnail_"+image.photo
                thumbnail = your_media_root + thumbnail_name
                # Rotate image based on orientation
                rotate_image(image_original)

                try:
                    # Generate Thumbnail
                    thumb = Image.open(image_original)
                    thumb.thumbnail(size, Image.LANCZOS)
                    thumb.save(thumbnail, quality=80, optimize=True)
                except Exception as e:
                    print(str(e))

                try:
                    # Uploading the image to s3
                    upload_image_s3(thumbnail, s3folder+thumbnail_name)
                except Exception as e:
                    print('Upload failed with reason %s', str(e))

                # Deleting the created thumbnail image and downloaded image
                time.sleep(2)
                delete([image_original, thumbnail])

            except (AttributeError, KeyError, IndexError):
                print('Image file not available in S3 bucket')
        else:
            thumbnail_name = 'profile.jpg'
        image.thumbnail = thumbnail_name
        image.save()


def rotate_image(image_original):
    """
        Rotate the image based on orientation
    """
    try:
        # Rotate the image
        rotateImage = Image.open(image_original)
        for orientation in ExifTags.TAGS.keys():
            if ExifTags.TAGS[orientation] == 'Orientation': break
        exif = dict(rotateImage._getexif().items())

        if exif[orientation] == 3:
            rotateImage = rotateImage.rotate(180, expand=True)
        elif exif[orientation] == 6:
            rotateImage = rotateImage.rotate(270, expand=True)
        elif exif[orientation] == 8:
            rotateImage = rotateImage.rotate(90, expand=True)
        rotateImage.save(image_original)
        rotateImage.close()
    except Exception as e:
        print(str(e))
        pass


@app.task
def generate_video_thumbnail(**kwargs):
    """
        Creating the video thumbnail from s3 uploaded video
    """
    imageio.plugins.ffmpeg.download()

    video_id = kwargs.pop('id', None)
    query_set = StargramVideo.objects.filter(thumbnail__isnull=True)
    if video_id:
        query_set = query_set.filter(id=video_id)
    videos = query_set
    config = Config.objects.get(key='stargram_videos')
    s3folder_video_thumb = Config.objects.get(key='stargram_video_thumb').value
    s3folder = config.value
    delete_water_mark_video = delete_logo = None

    print("Total videos: " + str(videos.count()))
    your_media_root = settings.MEDIA_ROOT + 'thumbnails/'
    watermark_location = your_media_root + 'watermark/'
    thumbnail_name = 'novideo.png'
    total_duration = '00:00:00'
    width = height = 0
    for request_video in videos:
        print("selected video is %s" % request_video)
        if check_file_exist_in_s3(s3folder + request_video.video) is not False:
            print("video exist in s3")
            try:
                video_name = request_video.video
                print("video_name is %s" % video_name)
                # Generating the pre-signed s3 URL
                video_url = get_pre_signed_get_url(video_name, s3folder)
                video_original = delete_original_video = your_media_root+video_name
                print("video_url is %s" % video_url)
                print("video in download folder in server : %s" % video_original)
                # Downloading video from s3
                urllib.request.urlretrieve(video_url, video_original)
                print("video downloaded")
                name = video_name.split(".", 1)[0]
                print("video_name is %s" % name)
                video_thumbnail_name = name+"_sg_thumbnail.jpg"
                video_thumb = your_media_root + video_thumbnail_name
                print("video thumbnail path : %s" % video_thumb)
                try:
                    print("trying video file clip")
                    VideoFileClip(video_original)
                except Exception:
                    print("video file clip exception")
                    new_file = your_media_root + 'DUP_%s.mp4' % name
                    fix_corrupted_video(video_original, new_file)
                    if not request_video.visibility:
                        try:
                            upload_image_s3(new_file, s3folder + request_video.video)
                        except Exception:
                            pass
                    video_original = new_file

                try:
                    # Creating the image thumbnail from the video
                    print("cliping started")
                    clip = VideoFileClip(video_original)
                    print("cliping successfull")
                    if clip.rotation in [90, 270]:
                        clip = clip.resize(clip.size[::-1])
                        clip.rotation = 0
                    print("first frame cutting started")
                    clip.save_frame(video_thumb, t=0.00)
                    print("first frame successfully selected and stored in : %s" % video_thumb)
                    width, height = clip.size
                    print("width : %s, height : %s" % (width, height))
                    duration = clip.duration
                    print("duration: %s" % duration)
                except Exception as e:
                    print("video file clip exception")
                    print(str(e))
                    continue
                print("starting watermarking, visibility : %s" % request_video.visibility)
                if request_video.visibility:
                    # Creating a water mark for video
                    if watermark_videos(video_original, name, your_media_root):
                        print("successfull watermarked")
                        if os.path.exists(watermark_location + "%s.mp4" % name):
                            for i in range(0, 3):
                                try:
                                    # Upload the video to s3
                                    upload_image_s3(watermark_location + "%s.mp4" % name, s3folder + "%s.mp4" % name)
                                    delete_water_mark_video = watermark_location + "%s.mp4" % name
                                    delete_logo = watermark_location + "%s_star.png" % name
                                    print('Uploaded Video to S3')
                                except Exception as e:
                                    print('Upload Video failed with reason %s', str(e))
                                    continue
                                break
                        else:
                            print('Video is not in path %s ' % watermark_location)
                    else:
                        print('watermark videos creation failed')

                m, s = divmod(duration, 60)
                h, m = divmod(m, 60)
                total_duration = "%02d:%02d:%02d" % (h, m, s)

                # Generate Video thumbnail
                im = Image.open(video_thumb)
                im.thumbnail(video_thumb_size, Image.LANCZOS)

                # Rotate video thumbnail
                print("Image has %d degree" % clip.rotation)
                if clip.rotation in [90, 270]:
                    print("Rotating the image by %d degrees" % clip.rotation)
                    im = im.rotate(-clip.rotation, expand=True)
                im.save(video_thumb, quality=99, optimize=True)

                try:
                    # Upload the thumbnail image to s3
                    upload_image_s3(video_thumb, s3folder_video_thumb+video_thumbnail_name)
                except Exception as e:
                    print('Upload failed with reason %s', str(e))

                # Save the video thumbnail in videos table
                thumbnail_name = video_thumbnail_name

                # Deleting the created thumbnail image and downloaded video
                print('Video- ' + video_name)
                time.sleep(2)
                list_to_delete = [delete_original_video, video_thumb]
                if delete_water_mark_video:
                    list_to_delete.append(delete_water_mark_video)
                if delete_logo:
                    list_to_delete.append(delete_logo)
                delete(list_to_delete)
            except Exception as e:
                print(str(e))
        else:
            thumbnail_name = 'novideo.png'
            total_duration = '00:00:00'

        request_video.thumbnail = thumbnail_name
        request_video.duration = total_duration
        request_video.width = width
        request_video.height = height
        request_video.save()

        if request_video.status == 1:
            try:
                bookings = Stargramrequest.objects.get(id=request_video.stragramz_request_id, request_status=4)
                bookings.request_status = 6
                bookings.save()
                print('Booking ID %s has been completed.' % str(request_video.stragramz_request_id))
            except Exception:
                pass

    print('Completed video thumbnail creations')


@app.task
def delete_unwanted_files():
    """
        Deleting images, thumbnails and profile video from s3 bucket
    """
    return True
    delete_photo_keys = {'Objects': []}
    delete_video_keys = {'Objects': []}
    s3 = boto3.client('s3', aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
                      aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'))

    # For deleting profile image and thumbnail files from S3 Bucket
    profile_image_prefix = Config.objects.get(key="profile_images")
    bucket_object_keys = get_bucket_objects(profile_image_prefix.value)
    no_delete_photo_list = ProfileImage.objects.values_list('photo', flat=True)
    no_delete_thumbnail_list = ProfileImage.objects.values_list('thumbnail', flat=True)
    photo_list = bucket_folder(no_delete_photo_list, profile_image_prefix.value)
    thumbnail_list = bucket_folder(no_delete_thumbnail_list, profile_image_prefix.value)

    list_keys = set([])
    if photo_list:
        list_keys = set(bucket_object_keys) - set(photo_list)
        bucket_object_keys = list_keys
    if thumbnail_list:
        list_keys = set(bucket_object_keys) - set(thumbnail_list)

    if len(list_keys) > 1 and bucket_object_keys:
        list_keys.remove(profile_image_prefix.value + 'profile.png')
        print(str(len(list_keys)) + ' Files deleted')
        delete_photo_keys['Objects'] = [{'Key': k} for k in list_keys]
        s3.delete_objects(Bucket=os.environ.get('AWS_STORAGE_BUCKET_NAME'), Delete=delete_photo_keys)

    # For deleting authentication video files from S3 Bucket
    authenticate_video_prefix = Config.objects.get(key="authentication_videos")
    bucket_object_keys = get_bucket_objects(authenticate_video_prefix.value)
    no_delete_video_list = Celebrity.objects.values_list('profile_video', flat=True)
    video_list = bucket_folder(no_delete_video_list, authenticate_video_prefix.value)
    if video_list and bucket_object_keys:
        field_names = set(bucket_object_keys) - set(video_list)

        if field_names:
            print(str(len(field_names)) +' Files deleted')
            delete_video_keys['Objects'] = [{'Key': k} for k in field_names]
            s3.delete_objects(Bucket=os.environ.get('AWS_STORAGE_BUCKET_NAME'), Delete=delete_video_keys)


def get_bucket_objects(prefix):
    """
        To get the list of all objects in a folder
    """
    s3 = boto3.client('s3', aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
                      aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'))
    bucket_object_keys = []
    all_objects = s3.list_objects(Bucket=os.environ.get('AWS_STORAGE_BUCKET_NAME'), Delimiter='/', Prefix=prefix)
    if len(all_objects['Contents']) > 1:
        for folder_objects in all_objects['Contents']:
            bucket_object_keys.append(folder_objects['Key'])
    return bucket_object_keys


def bucket_folder(list_to_append, bucket_folder):
    """
        To generate the bucket file Keys
    """
    resultant_list = []
    for list_items in list_to_append:
        resultant_list.append(bucket_folder+list_items)
    return resultant_list


def delete(files):
    """
        Delete the file from the location only after a day
    """
    current_time = time.time()
    for file in files:
        if os.path.isfile(file):
            creation_time = os.path.getctime(file)
            if (current_time - creation_time) // (24 * 3600) >= 1:
                os.remove(file)

    folders = [
        settings.MEDIA_ROOT + 'combined_videos/',
        settings.MEDIA_ROOT + 'thumbnails/watermark/',
        settings.MEDIA_ROOT + 'thumbnails/',
        settings.MEDIA_ROOT + 'uploads/'
    ]

    for folder in folders:
        for file in os.listdir(folder):
            file_path = os.path.join(folder, file)
            if os.path.isfile(file_path):
                creation_time = os.path.getctime(file_path)
                if (current_time - creation_time) // (24 * 3600) >= 1:
                    os.remove(file_path)


def check_file_exist_in_s3(file):
    """
        Method to check the image is available in s3 bucket
    """
    try:
        s3 = boto3.client('s3', aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
                          aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'))
        s3.head_object(Bucket=os.environ.get('AWS_STORAGE_BUCKET_NAME'), Key=file)
    except ClientError as e:
        print(str(e))
        return False
    return True


@app.task(name='create_monthly_payouts')
def create_payout_records():

    """
        Creating the records for processing the fund transfer for completed requests
    """
    print('Creating monthly payouts.')
    while 1:
        records = StarsonaTransaction.objects.filter(
            transaction_status=TRANSACTION_STATUS.captured,
            starsona__request_status=STATUS_TYPES.completed,
            amount__gt=1
        ).exclude(transaction_payout__status__in=PAYOUT_STATUS.get_key_values())[:1]

        for record in records:
            try:
                user = StargramzUser.objects.get(id=record.celebrity_id)
            except Exception as e:
                break
            if int(record.amount) > 0:
                print(user, record)
                if user.is_ambassador and record.ambassador_transaction:
                    field_defaults = {
                        'celebrity': user,
                        'fan_charged': float(round(record.amount, 2)),
                        'stripe_processing_fees': 0,
                        'starsona_company_charges': 0.0,
                        'fund_payed_out': float(round(record.actual_amount, 2)),
                        'status': PAYOUT_STATUS.check_pending if user.check_payments else PAYOUT_STATUS.pending
                    }
                    PaymentPayout.objects.update_or_create(
                        transaction_id=record.id,
                        defaults=field_defaults
                    )
                    continue
                if has_ambassador(record.celebrity_id):
                    starsona_charge = 20.0
                    referee_discount = 60.0
                else:
                    referee_discount = verify_referee_discount(record.celebrity_id)
                    starsona_charge = 25.0
                print("Referee discount is %d" % referee_discount)

                field_defaults = {
                    'celebrity': user,
                    'fan_charged': float(round(record.amount, 2)),
                    'stripe_processing_fees': 0,
                    'starsona_company_charges': 0.00 if referee_discount == 100 else float(in_app_price_reduction(record))*(starsona_charge/100.0),
                    'fund_payed_out': float(round((in_app_price_reduction(record)*(referee_discount/100.0)), 2)),
                    'status': PAYOUT_STATUS.check_pending if user.check_payments else PAYOUT_STATUS.pending
                }
                PaymentPayout.objects.update_or_create(
                    transaction_id=record.id,
                    defaults=field_defaults
                )
                if not has_ambassador(record.celebrity_id):
                    create_referral_payouts(record)
            else:
                print('Payout Amount must be greater than zero')

        if not records:
            send_payout.apply_async(eta=datetime.utcnow() + timedelta(minutes=3))
            print('Succesfully added %d records for processing' % records.count())
            break


def calculate_avg_sum(model_obj, field):
    amount = model_obj.aggregate(Sum(field))
    return amount[field+'__sum']


def checking_the_amount_dispatched(amount, allowable_amount):
    if amount < allowable_amount:
        return True
    return False


def verify_referee_discount(celebrity_id):
    """
        Verify the user has referee discounts
    """
    default_discount = 75.0

    try:
        referral_user = StargramzUser.objects.get(refer_referrer__referee_id=celebrity_id)
    except Exception:
        return default_discount

    try:
        campaign = Campaign.objects.get(id=referral_user.referral_campaign_id)
    except Exception:
        return default_discount

    celebrity = StargramzUser.objects.get(id=celebrity_id)
    paid_requests = PaymentPayout.objects.filter(celebrity=celebrity).count()

    if datetime.now().date() < campaign.valid_till \
            and campaign.request_for_user > paid_requests\
            and campaign.enable_two_way:
        return 100.0
    else:
        return default_discount


def create_referral_payouts(record):
    """
    Create payout for referral users
    :param record:
    :return:
    """
    try:
        referral_user = StargramzUser.objects.get(refer_referrer__referee_id=record.celebrity_id)
    except Exception:
        return True

    if referral_user and referral_user.referral_active:
        try:
            campaign = Campaign.objects.get(id=referral_user.referral_campaign_id)
        except Exception:
            return True

        users_amount = PaymentPayout.objects.filter(celebrity=referral_user, referral_payout=True) \
            .aggregate(payed_out=Sum('fund_payed_out'))
        referral_payed_out = float(0 if not users_amount.get('payed_out', None) else users_amount.get('payed_out'))

        # validate campaign
        if datetime.now().date() < campaign.valid_till and float(referral_payed_out) <= float(campaign.max_referral_amount):
            referral_amount = float(in_app_price_reduction(record)) * (25.0 / 100.0) * (int(campaign.discount)/100)
            amount = referral_payed_out + float(referral_amount)

            if amount > campaign.max_referral_amount:
                referral_amount = float(campaign.max_referral_amount) - referral_payed_out

            if referral_amount > 0:
                PaymentPayout.objects.create(
                    transaction_id=record.id,
                    celebrity=referral_user,
                    fan_charged=float(round(record.amount, 2)),
                    stripe_processing_fees=0,
                    starsona_company_charges=0.00,
                    fund_payed_out=float(referral_amount),
                    referral_payout=True,
                    comments="Referral amount from %s" % record.celebrity.get_short_name(),
                    status=PAYOUT_STATUS.check_pending if referral_user.check_payments else PAYOUT_STATUS.pending
                )

    return True


@app.task(name='resend_failed_payouts')
def resend_failed_payouts():
    """
        Resending the payouts which have failed during payout process
    """
    try:
        failed_payouts = PaymentPayout.objects.filter(status=PAYOUT_STATUS.payout_failed)

        for payouts in failed_payouts:
            payouts.status = PAYOUT_STATUS.pending
            payouts.save()

        send_payout.apply_async(eta=datetime.utcnow() + timedelta(minutes=3))
        print('Successfully updated %d records for reprocessing' % failed_payouts.count())
        return True
    except Exception as e:
        print(str(e))


@app.task
def send_payout():
    """
        Transferring amount to the celebrities linked stripe account
    """
    print('Sending out monthly payouts')
    stripe.api_key = SECRET_KEY
    amount_payed_out = 0
    user_paid = {}
    user_not_paid = {}
    user_failed = {}
    while 1:
        # Process the top 10 pending payments and breaks the
        # infinite true loop when there is no records to process
        pending_payouts = PaymentPayout.objects.filter(status=PAYOUT_STATUS.pending)[:10]

        if not pending_payouts:
            print('Payouts completed...')
            break

        current_payout = calculate_avg_sum(pending_payouts, 'fund_payed_out')
        amount_payed_out += current_payout

        if not amount_payed_out:
            print('No amount to payout')
            break

        balance = stripe.Balance.retrieve()
        available_balance = int(balance.available[0]['amount']/100)
        print("Total amount in Balance: %d" % int(available_balance))

        if available_balance > current_payout:

            print(current_payout)

            for payout in pending_payouts:
                try:
                    user = StargramzUser.objects.get(id=payout.celebrity_id)
                except Exception as e:
                    print('Celebrity users are only paid')
                    update_payout(payout, 'users is not a celebrity')
                    break

                if user.stripe_user_id:
                    try:
                        account = stripe.Account.retrieve(user.stripe_user_id)
                        account.payout_schedule['interval'] = 'daily'
                        account.save()
                    except stripe.error.StripeError as e:
                        print(str(e))
                        update_payout(payout, str(e))
                        user_failed = valid_dict(user_failed, user, payout.fund_payed_out, str(e))
                        break

                    try:
                        transfer = stripe.Transfer.create(
                            amount=int(float(payout.fund_payed_out)*100),
                            currency="usd",
                            destination=user.stripe_user_id,
                            description=""
                        )

                        payout.status = PAYOUT_STATUS.transferred
                        payout.stripe_transaction_id = transfer.id
                        payout.stripe_response = json.dumps(transfer)
                        payout.save()
                        user_paid = valid_dict(user_paid, user, payout.fund_payed_out, 'Paid out')
                    except stripe.error.StripeError as e:
                        print(str(e))
                        user_failed = valid_dict(user_failed, user, payout.fund_payed_out, str(e))
                        update_payout(payout, str(e))
                        break
                else:
                    print('Celebrity users doesnt have a stripe account')
                    update_payout(payout, 'Celebrity users doesnt have a stripe account')
                    user_not_paid = valid_dict(
                        user_not_paid,
                        user,
                        payout.fund_payed_out,
                        'Celebrity users doesnt have a stripe account'
                    )

            print('Completed the celebrity payouts.')
        else:
            send_payout.apply_async(eta=datetime.utcnow() + timedelta(days=1))
            break

    for key, values in user_not_paid.items():
        notify_users_on_payouts(values, 'Starsona payouts failed', 'not-paid')

    print('Notified Not paid out users.')

    for key, values in user_paid.items():
        notify_users_on_payouts(values, 'Starsona payouts for Month %s' % datetime.now().strftime("%B"), 'payouts')
    print('Notified paid users.')
    print('Notified Admin.')
    notify_admin(user_paid, user_not_paid, user_failed, 'Starsona payouts for Month %s' % datetime.now().strftime("%B"))

    return True


def update_payout(payout, comments):
    """
        Update the payouts
    """
    payout.status = 4
    payout.comments = '%s, %s' % (payout.comments, comments)
    payout.save()
    return True


def valid_dict(user_dict, user, amount, message):

    """
        Create Dict for user if user is not in the Dict
    """

    amount = float(amount)
    if user.username in user_dict:
        user_dict[user.username]['amount'] = user_dict[user.username]['amount'] + amount
        user_dict[user.username]['pay_count'] = user_dict[user.username]['pay_count']+1
    else:
        user_dict[user.username] = {
            'name': user.get_short_name(),
            'amount': amount,
            'pay_count': 1,
            'id': user.pk,
            'email': user.email,
            'reason': message,
        }

    return user_dict


def notify_users_on_payouts(user_dict, subject, template):
    """
        Notify user via Emails regarding payouts
    """
    ctx = {
        'base_url': BASE_URL,
        'name': user_dict['name'],
        'amount': format(user_dict['amount'], '.2f'),
        'pay_count': user_dict['pay_count'],
    }

    return sent_email(user_dict['email'], subject, template, ctx)


def notify_admin(paid, not_paid, failed, subject):
    support_email = Config.objects.get(key='support_email').value

    ctx = {
        'paid_users': paid,
        'not_paid_users': not_paid,
        'failed_users': failed,
    }

    return sent_email(support_email, subject, 'payouts-admin', ctx)


@app.task
def send_email_notification(request_id):

    """
        Send Email notifications to users on changes in request changes
    """
    try:
        request = Stargramrequest.objects.get(id=request_id)
    except Exception as e:
        print(str(e))
        return False

    try:
        celebrity = StargramzUser.objects.get(id=request.celebrity_id)
    except Exception as e:
        print(str(e))

    try:
        fan = StargramzUser.objects.get(id=request.fan_id)
    except Exception as e:
        print(str(e))

    occasion = ''
    try:
        occasion = Occasion.objects.get(id=request.occasion_id).title
    except Exception as e:
        print(str(e))

    email_notify = True
    if request.request_status in [5, 6]:
        email_notify = verify_user_for_notifications(request.fan_id, 'fan_email_starsona_videos')
    if request.request_status == 2:
        email_notify = verify_user_for_notifications(request.celebrity_id, 'celebrity_starsona_request')

    if not email_notify:
        print('Email notification is disabled for the user.')
        return True

    if request.request_status in [2, 5, 6, 7]:
        details = {
            'subject_2': 'New Starsona %s Request' % occasion,
            'template_2': 'request_confirmation',
            'email_2': celebrity.email,
            'subject_5': 'Cancelled Starsona Request',
            'template_5': 'request_cancelled' if not request.comment else 'request_cancelled_from_celebrity',
            'email_5': fan.email,
            'subject_6': 'Your Starsona video is ready',
            'template_6': 'video_completed_with_reprocessing' if request.reprocessed else 'video_completed',
            'email_6': fan.email,
            'subject_7': 'Starsona booking is ready for reprocessing',
            'template_7': 'booking_reprocessing',
            'email_7': celebrity.email,
        }

        subject = details['subject_%d' % request.request_status]
        email = details['email_%d' % request.request_status]
        template = details['template_%d' % request.request_status]
        sender_email = Config.objects.get(key='sender_email').value
        if request.request_status == 2:
            # inform the representative of the celebrity about this booking
            representative_notify(celebrity, fan, occasion)
        try:
            data = json.loads(request.request_details)
        except Exception:
            data = ''
        date = ''
        if 'date' in data and data['date']:
            try:
                date = datetime.strptime(data['date'], "%Y-%m-%dT%H:%M:%S.%fZ").strftime('%B %d, %Y')
            except Exception:
                pass
        if request.request_type == REQUEST_TYPES.personalised_video:
            request_type = 'shout-out'
        elif request.request_type == REQUEST_TYPES.event_announcement:
            request_type = 'event'
        else:
            request_type = ''

        ctx = {
            'base_url': BASE_URL,
            'celebrity_name': celebrity.get_short_name(),
            'fan_name': fan.get_short_name(),
            'occasion': occasion,
            'id': hashids.encode(request.id),
            'important_info': data['important_info'] if 'important_info' in data else '',
            'to_name': data['stargramto'] if 'stargramto' in data else '',
            'from_name': data['stargramfrom'] if 'stargramfrom' in data else '',
            'date': date,
            'relationship': data['relationship']['title'] if 'relationship' in data else '',
            'request_type': request_type
        }
        video_id = None
        video_url = BASE_URL
        if request.request_status == 6:
            try:
                video_id = StargramVideo.objects.values_list('id', flat=True).get(stragramz_request_id=request.id, status=1)
                web_url = Config.objects.get(key="web_url").value
                video_url = "%svideo/%s" % (web_url, hashids.encode(video_id))
            except Exception:
                pass

        web_url = Config.objects.get(key='web_url').value
        urls = {
            2: '%smanage/bookings?type=open&selected=%s' % (web_url, hashids.encode(request.id)),
            5: BASE_URL,
            6: video_url,
            7: '%smanage/bookings?type=open&selected=%s' % (web_url, hashids.encode(request.id))
        }

        app_urls = {
            2: 'request/?request_id=%s&role=R1002' % hashids.encode(request.id),
            5: 'home/',
            6: 'video/?video_id=%s' % hashids.encode(video_id) if video_id else None,
            7: 'request/?request_id=%s&role=R1002' % hashids.encode(request.id)
        }

        canonical_url = {
            2: '%srequest/R1002/%s' % (web_url, encode_pk(request.id)),
            5: BASE_URL,
            6: video_url,
            7: '%srequest/R1002/%s' % (web_url, encode_pk(request.id)),
        }

        ctx['app_url'] = video_url if request.request_status == 6 else generate_branch_io_url(
            title=subject,
            desc=subject,
            mob_url=app_urls[request.request_status],
            desktop_url=urls[request.request_status],
            canonical_url=canonical_url[request.request_status],
            image_url='%smedia/web-images/starsona_logo.png' % BASE_URL,
        )

        try:
            html_template = get_template('../templates/emails/%s.html' % template)
            html_content = html_template.render(ctx)
        except Exception as e:
            print(str(e))

        try:
            SendMail(subject, html_content, sender_email=sender_email, to=email)
        except Exception as e:
            print(str(e))

    return True


def watermark_videos(video_original, name, your_media_root):
    """
        Adding Starsona Logo on celebrity uploaded videos
    """
    try:
        watermark_location = your_media_root+"watermark/"
        if os.path.exists(video_original):
            video = VideoFileClip(video_original)
            # video = video_rotation(video)
            if video.rotation == 90 or video.rotation == 270:
                video = video.resize(video.size[::-1])
                video.rotation = 0
            logo_size = 0.4*video.size[0], 0.4*video.size[1]
            im = Image.open(your_media_root+"../web-images/starsona_logo.png")
            im.thumbnail(logo_size)
            logo = (ImageClip(your_media_root+"../web-images/starsona_logo.png")
                    .set_duration(video.duration)
                    .resize(height=0.1*video.size[0], width=0.1*video.size[1])  # if you need to resize...
                    .margin(right=10, bottom=10, opacity=0)  # (optional) logo-border padding
                    .set_pos(("right", "bottom")))
            watermark_location_video = watermark_location + "%s.mp4"
            final_clip = CompositeVideoClip([video, logo])
            final_clip.write_videofile(
                watermark_location_video % name,
                audio_codec='aac',
                progress_bar=False,
                verbose=False,
                threads=4,
                ffmpeg_params=['-movflags', '+faststart']
            )
            return True
        else:
            print('File Not exist')
            return False
    except Exception as e:
        print('Error in watermark_videos %s : start watermark creation in 10 Seconds' % str(e))
        time.sleep(10)
        generate_video_thumbnail.delay()
        return False


@app.task
def combine_video_clips(request_id):
    """
        Combine two videos to one with same resolution
    """
    request_videos = StargramVideo.objects.filter(
        stragramz_request_id=request_id,
        status__in=[4, 5]
    ).order_by('created_date')

    config = Config.objects.get(key='stargram_videos')
    your_media_root = settings.MEDIA_ROOT + 'combined_videos/'
    s3folder = config.value

    files = []
    for video in request_videos:
        if check_file_exist_in_s3(s3folder + video.video) is not False:
            print('Downloading files... %s' % video.video)
            video_file = download_file(video.video, s3folder, your_media_root)
            while not video_file:
                time.sleep(2)
                video_file = download_file(video.video, s3folder, your_media_root)

            files.append(video_file)
        else:
            print('File not exists.')

    if files and len(files) == 2:
        try:
            combined_video_name = "CMBD_%s.mp4" % str(int(time.time()))
            video_1_name = "V1_%s.mp4" % str(int(time.time()))
            video_2_name = "V2_%s.mp4" % str(int(time.time()))

            try:
                VideoFileClip(files[0])
            except Exception:
                new_file = your_media_root + 'DUP_%s.mp4' % str(int(time.time()))
                fix_corrupted_video(files[0], new_file)
                files[0] = new_file


            clip1 = VideoFileClip(files[0])
            #clip1 = video_rotation(clip1)
            if clip1.rotation == 90 or clip1.rotation == 270:
                clip1 = clip1.resize(clip1.size[::-1])
                clip1.rotation = 0

            clip1.write_videofile(
                your_media_root + video_1_name,
                audio_codec='aac',
                progress_bar=False,
                verbose=False,
                threads=2,
                ffmpeg_params=['-movflags', '+faststart']
            )

            try:
                VideoFileClip(files[1])
            except Exception:
                new_file = your_media_root + 'DUP_%s.mp4' % str(int(time.time()))
                fix_corrupted_video(files[1], new_file)
                files[1] = new_file

            clip2 = VideoFileClip(files[1])
            #clip2 = video_rotation(clip2)
            if clip2.rotation == 90 or clip2.rotation == 270:
                clip2 = clip2.resize(clip2.size[::-1])
                clip2.rotation = 0

            clip2.write_videofile(
                your_media_root+video_2_name,
                audio_codec='aac',
                progress_bar=False,
                verbose=False,
                threads=2,
                ffmpeg_params = ['-movflags', '+faststart']
            )

            width, height = clip1.size
            clip1_height = int((height / width * 640)/2) * 2

            width, height = clip2.size
            clip2_height = int((height / width * 640)/2) * 2

            newclip1 = resize(clip1, newsize=(640, clip1_height))
            newclip2 = resize(clip2, newsize=(640, clip2_height))

            final_clip = concatenate_videoclips(
                [newclip1, newclip2.fx(transfx.slide_in, duration=0.5, side='left')],
                method='compose',
                padding=0.5,
            )

            final_clip.write_videofile(
                your_media_root + combined_video_name,
                audio_codec='aac',
                progress_bar=False,
                verbose=False,
                threads=2
            )

            if os.path.exists(your_media_root + combined_video_name):
                try:
                    StargramVideo.objects.get(stragramz_request_id=request_id, status=1)
                    print('Already created video...')
                except Exception:
                    upload_image_s3(your_media_root + combined_video_name, s3folder + combined_video_name)
                    new_video = StargramVideo.objects.create(
                        stragramz_request_id=request_id,
                        video=combined_video_name,
                        status=VIDEO_STATUS.completed,
                        visibility=True
                    )
                    generate_video_thumbnail.delay(id=new_video.id)
                    print('Generate video thumbnail for new file...')
                    for video in request_videos:
                        video.thumbnail = None
                        video.visibility = True
                        video.save()
                        generate_video_thumbnail.delay(id=video.id)
                    print('Created new combined video...')
        except Exception as e:
            print(str(e))


def download_file(video, s3folder, your_media_root):
    # Generating the pre-signed s3 URL
    video_url = get_pre_signed_get_url(video, s3folder)
    video_download = your_media_root + video

    if not os.path.exists(your_media_root):
        os.makedirs(your_media_root)

    try:
        # Downloading video from s3
        urllib.request.urlretrieve(video_url, video_download)
    except Exception:
        return False

    return video_download


@app.task(name='update_video_width_and_height')
def update_video_width_and_height():
    """
        Update the width and height of video
    """
    video_folder = settings.MEDIA_ROOT + 'videos/'

    while 1:
        request_videos = StargramVideo.objects.filter(width=None)[:10]
        if not request_videos:
            print('Videos completed...')
            break

        for video in request_videos:
            video_download = video_folder + video.video

            s3folder = 'videos/stargram_videos/'
            video_url = get_pre_signed_get_url(video.video, s3folder)
            try:
                print('Downloading files... %s' % video.video)
                urllib.request.urlretrieve(video_url, video_download)
                if video_download:
                    clip = VideoFileClip(video_download)
                    width, height = clip.size
                    video.width = width
                    video.height = height
                    video.save()
                    print('Saved Video %s', video.video)
                    os.remove(video_download)
                    print('Deleted the Video %s', video_download)
            except Exception:
                print('Download Failed...')

    print('Completed the video size fix')


def fix_corrupted_video(video_file, new_video_file):
    """
    Fixing issue with the corrupted video
    :param video_file: Video original path
    :param new_video_file: New video path
    :return:
    """
    print("in fix_corrupted_video with video file : %s" % video_file)
    if os.path.exists(video_file) and os.path.getsize(video_file) > 10:
        sender_email = Config.objects.get(key='sender_email').value
        SendMail('Fixing Corrupted video', 'Fixing Corrupted video %s' % video_file, sender_email=sender_email, to='akhilns@qburst.com')
        return os.system("ffmpeg -i %s -r 30000/1001 -strict -2 -vcodec libx264 -acodec aac %s" % (video_file, new_video_file))
    else:
        return False


@app.task
def convert_audio(booking_id):
    """
    Convert the webm audio file to m4a to make it audible in mobile apps(iOS and Android)

    :param booking_id
    :return: boolean
    """
    your_audio_root = settings.MEDIA_ROOT + 'uploads/'
    booking = Stargramrequest.objects.get(id=booking_id)
    is_update = False
    if booking.from_audio_file:
        booking.from_audio_file = process_audio_file(booking.from_audio_file, your_audio_root)
        is_update = True
    if booking.to_audio_file:
        booking.to_audio_file = process_audio_file(booking.to_audio_file, your_audio_root)
        is_update = True

    if is_update:
        booking.save()

    return True


def process_audio_file(audio, audio_root):
    """
    Processing audio file download the audio file, convert the webm file and uploads
    :param audio: Audio file path
    :param audio_root: path of audio folder
    :return s3_file_name: Name of the s3 file
    """
    if not os.path.exists(audio_root):
        os.makedirs(audio_root)
    if check_file_exist_in_s3(audio) is not False:
        audio_name = audio.replace('audio/', '')
        audio_file = download_file(audio_name, 'audio/', audio_root)
        name = audio_name.split(".", 1)[0]
        extension = audio_name.split(".", 1)[1]
        s3_file_name = 'audio/%s.m4a' % name
        if extension.lower() == 'webm':
            new_audio_file = "%s%s.m4a" % (audio_root, name)
            convert_audio_file(audio_file, new_audio_file)
            try:
                upload_image_s3(new_audio_file, s3_file_name)
            except Exception:
                return audio
        return s3_file_name
    else:
        return audio


def convert_audio_file(audio_file, new_audio_file):
    """
    Converting webm to m4a
    """
    if os.path.exists(audio_file) and os.path.getsize(audio_file) > 10:
        return os.system("ffmpeg -i %s -strict -2 %s" % (audio_file, new_audio_file))
    else:
        return False


# @app.task(name='reprocess_pending_video_approval')
def reprocess_pending_video_approval():
    """
    Get all the list of bookings which are in video approval status
    :return: Boolean
    """
    try:
        requests = Stargramrequest.objects.filter(
            request_status=4,
            request_transaction__modified_date__lt=datetime.utcnow() - timedelta(hours=12)
        )

        s3folder = Config.objects.get(key='stargram_videos').value
        sender_email = Config.objects.get(key='sender_email').value
        for request in requests:
            # Processing all bookings in video approval status and not processed for 6hrs
            booking_videos = StargramVideo.objects.filter(stragramz_request_id=request.id)
            files = []
            video_id = None
            for video in booking_videos:
                video_id = video.id
                if check_file_exist_in_s3(s3folder + video.video) is not False:
                    files.append(video.video)

            # Check bookings type and re-applying the video generation tasks
            if request.request_type in [1, 2] and len(files) == 1:
                # Generating the video watermark for the video
                generate_video_thumbnail.delay(id=video_id)
            elif request.request_type == 3 and len(files) == 2:
                # Processing the Q&A video for merging videos
                combine_video_clips.delay(request.id)
            else:
                # Sending email with the link of booking and canceling the booking
                content = "Booking ID %d has been cancelled and amount has been refunded as video is not available in" \
                          " S3 server %s/admin/stargramz/stargramrequest/%d/change" % (request.id, BASE_URL, request.id)

                SendMail('Auto canceling videos', content, sender_email=sender_email, to='akhilns@qburst.com')
                request.request_status = STATUS_TYPES.cancelled
                request.save()
    except Exception as e:
        print(str(e))
    return True


@contextmanager
def memcache_lock(lock_id, oid):
    """
    Check to execute the task only once, store the lock in cache for 1 hr
    :param lock_id:
    :param oid:
    :return: Boolean
    """
    status = cache.add(lock_id, oid, 3600)
    yield status


@app.task
def notify_fan_reaction_videos_and_feedback(booking_id):
    from notification.tasks import send_notification
    """
    Triggering Push/email notifications to fan to add review and share there reaction
    videos with starsona for completed bookings
    :param booking_id:
    :return:
    """
    lock_id = '{0}-lock-{1}'.format('reaction_video', booking_id)
    with memcache_lock(lock_id, app.oid) as acquired:
        if not acquired:
            return True

    print("Reaction for %d" % booking_id)
    if Reaction.objects.filter(booking_id=booking_id).count() == 0:
        print('Adding reactions...')
        try:
            requests = Stargramrequest.objects.get(id=booking_id)
        except Exception:
            return True
        booking_hash_id = hashids.encode(booking_id)
        data = {'type': NOTIFICATION_TYPES.pending_reaction_video, 'role': ROLES.fan, 'id': booking_hash_id}
        send_notification.delay(
            requests.fan_id,
            PENDING_REACTION_VIDEO_TITLE,
            PENDING_REACTION_VIDEO_BODY % requests.celebrity.get_short_name(),
            data,
            field='celebrity_starsona_request'
        )
        try:
            video_thumbnail = StargramVideo.objects.values_list('thumbnail', flat=True).get(
                stragramz_request_id=booking_id, status=1
            )
        except Exception:
            return True

        base_url = Config.objects.get(key='base_url').value
        web_url = Config.objects.get(key='web_url').value
        ctx = {'celebrity_name': requests.celebrity.get_short_name(),
               'fan_name': requests.fan.get_short_name(),
               'booking_title': requests.booking_title,
               'video_thumb': '{}/{}'.format(get_bucket_url(), STARGRAM_VIDEO_THUMB + video_thumbnail),
               'app_url': generate_branch_io_url(
                    title="Add reaction videos",
                    desc="Add review and share your reaction videos",
                    canonical_url='%sapplinks/reactions/%s' % (base_url, booking_hash_id),
                    mob_url='reactions/%s' % booking_hash_id,
                    desktop_url='%smanage/my-videos?request_id=%s' % (web_url, booking_hash_id),
                    image_url='%smedia/web-images/starsona_logo.png' % base_url,
                )}
        fan_email = requests.fan.email
        sent_email(fan_email, 'Share your reaction with %s' % requests.celebrity.get_short_name(), 'add_reaction_videos', ctx)
        print('Notified fan for reaction videos')
        return True
    else:
        print('Already added reactions')
        return True


@app.task(name='generate_reaction_videos')
def generate_reaction_videos(reaction_id):
    """
        Creating the reaction video thumbnail from s3 uploaded video
    """
    imageio.plugins.ffmpeg.download()

    if reaction_id:
        reactions = Reaction.objects.get(id=reaction_id, file_type=2, file_thumbnail__isnull=True)
    else:
        return True

    s3folder_video_thumb = 'reactions/thumbnails/'
    s3folder = 'reactions/'

    your_media_root = settings.MEDIA_ROOT + 'thumbnails/'
    watermark_location = your_media_root + 'watermark/'
    width = height = 0
    print('before s3 file check')
    if check_file_exist_in_s3(s3folder + reactions.reaction_file) is not False:
        print('reaction file exist in S3')
        try:
            video_name = reactions.reaction_file

            # Generating the pre-signed s3 URL
            video_url = get_pre_signed_get_url(video_name, s3folder)
            video_original = delete_original_video = your_media_root + video_name
            print('reaction original video - %s', video_original)

            # Downloading video from s3
            urllib.request.urlretrieve(video_url, video_original)
            name = video_name.split(".", 1)[0]
            video_thumbnail_name = re.sub('[^a-zA-Z0-9]', '', name) + "_thumbnail.jpg"
            video_thumb = your_media_root + video_thumbnail_name
            print("reaction video downloaded")

            try:
                print("reaction video clipping started")
                VideoFileClip(video_original)
            except Exception:
                print("reaction video clipping exception")
                new_file = your_media_root + 'REACTIONS_%s.mp4' % name
                fix_corrupted_video(video_original, new_file)
                try:
                    upload_image_s3(new_file, s3folder + reactions.reaction_file)
                except Exception:
                    pass
                video_original = new_file

            try:
                # Creating the image thumbnail from the video
                print("reaction thumbnail")
                clip = VideoFileClip(video_original)
                if clip.rotation in [90, 270]:
                    clip = clip.resize(clip.size[::-1])
                    clip.rotation = 0
                clip.save_frame(video_thumb, t=0.00)
                width, height = clip.size

                duration = clip.duration
            except Exception as e:
                print("thumbnail generation failed")
                print(str(e))

            # Creating a water mark for video
            if watermark_videos(video_original, name, your_media_root):
                print("reaction video watermarking success")
                if os.path.exists(watermark_location + "%s.mp4" % name):
                    for i in range(0, 3):
                        try:
                            # Upload the video to s3
                            upload_image_s3(watermark_location + "%s.mp4" % name, s3folder + "%s.mp4" % name)
                            print('Uploaded Video to S3')
                        except Exception as e:
                            print('Upload Video failed with reason %s', str(e))
                            continue
                        break
                else:
                    print('Video is not in path %s ' % watermark_location)
            else:
                print('watermark videos creation failed')

            m, s = divmod(duration, 60)
            h, m = divmod(m, 60)
            total_duration = "%02d:%02d:%02d" % (h, m, s)

            # Generate Video thumbnail
            im = Image.open(video_thumb)
            im.thumbnail(video_thumb_size, Image.LANCZOS)

            # Rotate video thumbnail
            print("Image has %d degree" % clip.rotation)
            if clip.rotation in [90, 270]:
                print("Rotating the image by %d degrees" % clip.rotation)
                im = im.rotate(-clip.rotation, expand=True)
            im.save(video_thumb, quality=99, optimize=True)

            try:
                # Upload the thumbnail image to s3
                upload_image_s3(video_thumb, s3folder_video_thumb + video_thumbnail_name)
            except Exception as e:
                print('Upload failed with reason %s', str(e))

            # Save the video thumbnail in videos table
            thumbnail_name = video_thumbnail_name

            # Deleting the created thumbnail image and downloaded video
            print('Video- ' + video_name)
            reactions.file_thumbnail = thumbnail_name
            reactions.duration = total_duration
            reactions.width = width
            reactions.height = height
            reactions.save()
            time.sleep(2)

        except (AttributeError, KeyError, IndexError):
            print('Video file not available in S3 bucket.')

        print('Completed reactions thumbnail creations.')


@app.task(name='generate_reaction_image')
def generate_reaction_image(reaction_id):
    """
        Generate thumbnail for reactions image
    """

    if reaction_id:
        reactions = Reaction.objects.get(id=reaction_id, file_type=1, file_thumbnail__isnull=True)
    else:
        return True

    your_media_root = settings.MEDIA_ROOT + 'thumbnails/'
    s3folder = 'reactions/'
    s3folder_thumb = 'reactions/thumbnails/'

    img_url = get_pre_signed_get_url(reactions.reaction_file, s3folder)
    image_original = your_media_root + reactions.reaction_file
    print("reaction image: " + reactions.reaction_file)
    if check_file_exist_in_s3(s3folder + reactions.reaction_file) is not False:
        try:
            # Downloading the image from s3
            urllib.request.urlretrieve(img_url, image_original)
            thumbnail_name = "reaction_thumbnail_" + reactions.reaction_file
            thumbnail = your_media_root + thumbnail_name
            new_image_original = your_media_root + reactions.reaction_file
            # Rotate image based on orientation
            rotate_image(image_original)

            try:
                # Generate Thumbnail
                thumb = Image.open(image_original)
                thumb.thumbnail(size, Image.LANCZOS)
                thumb.save(thumbnail, quality=80, optimize=True)

                main_image = Image.open(image_original)
                main_image.save(new_image_original, quality=80, optimize=True)
            except Exception as e:
                print(str(e))

            try:
                # Uploading the image to s3
                upload_image_s3(thumbnail, s3folder_thumb + thumbnail_name)
                upload_image_s3(image_original, s3folder + reactions.reaction_file)
            except Exception as e:
                print('Upload failed with reason %s', str(e))

            # Deleting the created thumbnail image and downloaded image
            time.sleep(2)

        except (AttributeError, KeyError, IndexError):
            print('Image file not available in S3 bucket')
        reactions.file_thumbnail = thumbnail_name
        reactions.save()
        print('Thumbnail image uploaded to S3 bucket')
    else:
        print('File not found.')


@app.task
def group_notify(group_details):
    """
        Send a notification mail to the group when a celebrity supports it
    :param group_details:
    :return:
    """
    web_url = Config.objects.get(key='web_url').value
    for group in group_details:
        try:
            group = CelebrityGroupAccount.objects.get(id=group)
            ctx = {
                'account_name': group.account.get_short_name(),
                'celebrity_name': group.user.get_short_name(),
                'redirect_link': generate_branch_io_url(
                    desktop_url='%suser/star-supporters' % web_url,
                    mob_url='%ssettings' % BASE_URL,
                    image_url='%smedia/web-images/starsona_logo.png' % BASE_URL,
                    title='Group Joining Request',
                    desc='Group Joining Request',
                )
            }
            sent_email(group.account.email, 'Group Invite Request', 'group_join_notify', ctx)
        except Exception:
            pass


@app.task
def invite_celebrity_notify(group_details):
    """
        Send a notification mail to the celebrity when group invites that celebrity
    :param group_details:
    :return:
    """
    web_url = Config.objects.get(key='web_url').value
    for group in group_details:
        try:
            group = CelebrityGroupAccount.objects.get(id=group)
            ctx = {
                'account_name': group.account.get_short_name(),
                'celebrity_name': group.user.get_short_name(),
                'redirect_link': generate_branch_io_url(
                    desktop_url='%suser/my-groups' % web_url,
                    mob_url='%ssettings' % BASE_URL,
                    image_url='%smedia/web-images/starsona_logo.png' % BASE_URL,
                    title='Group Invite',
                    desc='Group Invite',
                ),
            }
            sent_email(group.user.email, 'Group Invite', 'group_invite_notify', ctx)
        except Exception:
            pass

@app.task
def send_sms_celebrity(message, celebrity_id):
    try:
        celebrity = StargramzUser.objects.get(id=celebrity_id)
        phone = SettingsNotifications.objects.get(user=celebrity.id, mobile_notification=True)
        if phone.mobile_country_code and phone.mobile_number:
            country_code = phone.mobile_country_code[1:] if phone.mobile_country_code[0] == '+' else phone.mobile_country_code
            phone_number = "+%s%s" % (country_code, phone.mobile_number)
            send_sms.delay(message, phone_number)
            return True
        else:
            return False
    except Exception as e:
        print(str(e))
        return False


@app.task
def send_sms(message, to):
    """
     The function send a text message to any number in international format
    :param message:
    :param to:
    :return:
    """
    account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
    auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
    from_number = os.environ.get('TWILIO_PHONE_NUMBER')

    try:
        client = Client(account_sid, auth_token)

        message = client.messages.create(
            body=message,
            from_=from_number,
            to=to
        )
    except Exception:
        return False
    return True


@app.task
def send_admin_mail(subject, template, ctx):
    """
    The function will send the template with given context to the admin
    :param subject:
    :param template:
    :param ctx:
    :return:
    """
    try:
        to_email = Config.objects.get(key="admin_email").value
        sent_email(to_email, subject, template, ctx)
        return True
    except Exception:
        return False


@app.task
def send_message_to_slack(template, ctx):
    try:
        slack_message('slack/%s.slack' % template, ctx)
        return True
    except Exception as e:
        print(str(e))
        return False

@app.task
def request_slack_message(request_id):
    try:
        booking = Stargramrequest.objects.get(id=request_id)
        slack_template = ""
        slack_ctx = {}
        if booking.request_status is STATUS_TYPES.completed:
            # This script below will send slack message when the request is completed
            slack_template = "video_completed"
            web_url = Config.objects.get(key="web_url").value
            video = StargramVideo.objects.get(stragramz_request=booking, status=1)
            slack_ctx = {
                "fan_name": booking.fan.get_short_name(),
                "celebrity_name": booking.celebrity.get_short_name(),
                "video_link": "%svideo/%s" % (web_url, encode_pk(video.id))
            }
        elif booking.request_status is STATUS_TYPES.pending:
            # This script will send slack message when a new request is completed its edit time
            slack_template = "new_booking"
            slack_ctx = {
                "fan_name": booking.fan.get_short_name(),
                "celebrity_name": booking.celebrity.get_short_name(),
                "type":  REQUEST_TYPES.get_label(booking.request_type),
            }
        send_message_to_slack.delay(slack_template, slack_ctx)
    except Exception as e:
        print(str(e))


@app.task
def generate_medium_thumbnail(celebrity_user_ids):
    """
        Generate medium thumbnail for the profile photos and upload to s3
    """
    images = ProfileImage.objects.filter(user_id__in=celebrity_user_ids)
    config = Config.objects.get(key='profile_images')
    your_media_root = settings.MEDIA_ROOT + 'thumbnails/'
    s3folder = config.value

    for image in images:
        img_url = get_pre_signed_get_url(image.photo, s3folder)
        image_original = your_media_root+image.photo
        print("image: "+image.photo)
        thumbnail_name = "thumbnail_medium_" + image.photo
        thumbnail = your_media_root + thumbnail_name
        if check_file_exist_in_s3(s3folder+image.photo) is not False:
            try:
                # Downloading the image from s3
                urllib.request.urlretrieve(img_url, image_original)
                # Rotate image based on orientation
                rotate_image(image_original)

                try:
                    # Generate Medium Thumbnail
                    thumb = Image.open(image_original)
                    thumb.save(thumbnail, quality=80, optimize=True)
                except Exception as e:
                    print(str(e))

                try:
                    # Uploading the image to s3
                    if check_file_exist_in_s3(s3folder+thumbnail_name) is False:
                        upload_image_s3(thumbnail, s3folder+thumbnail_name)
                except Exception as e:
                    print('Upload failed with reason %s', str(e))

                # Deleting the created thumbnail image and downloaded image
                time.sleep(2)
                delete([image_original, thumbnail])

            except (AttributeError, KeyError, IndexError):
                print('Image file not available in S3 bucket')
        else:
            thumbnail_name = 'profile.jpg'

        image.medium_thumbnail = thumbnail_name
        image.save()

