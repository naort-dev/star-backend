import datetime
from job.tasks import check_file_exist_in_s3
import boto3
import os
from payments.models import StarsonaTransaction, TRANSACTION_STATUS, PAYOUT_STATUS, TipPayment, TIP_STATUS, PaymentPayout
from stargramz.models import STATUS_TYPES, StargramVideo, Comment, Reaction, FILE_TYPES, Stargramrequest
from users.models import FanRating, Celebrity, Referral, Campaign
from django.db.models import Sum
from django.utils import timezone
import datetime
import pytz

def date_format_conversion(date):
    """
    The Function will convert the format of the expiry date in the register version 2 API into suitable format
    suitable format : YYYY-MM-DD HH:MM[:ss[.uuuuuu]][TZ].
    :param date:
    :return:
    """
    if date:
        elements = date.split(" ")
        elements = elements[1:5]
        date = " ".join(elements)
        date = datetime.datetime.strptime(date, '%b %d %Y %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S.%f+05:30')
        return date
    else:
        return None


def remove_files_from_s3(file):
    try:
        if check_file_exist_in_s3(file):
            objects = {'Objects': [{'Key': file}]}
            s3 = boto3.client('s3', aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
                              aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'))
            s3.delete_objects(Bucket=os.environ.get('AWS_STORAGE_BUCKET_NAME'), Delete=objects)
            print('The file : %s is successfully deleted from s3' % file)
    except Exception as e:
        print(str(e))


# Dashboard updating functions

def total_earnings_update(dashboard):
    """
    updating the earnings of the user into his dashboard
    :param dashboard:
    :return:
    """
    user = dashboard.user
    query_set = StarsonaTransaction.objects.filter(
        celebrity_id=user.id,
        starsona__request_status=STATUS_TYPES.completed,
        transaction_status=TRANSACTION_STATUS.captured
    ).prefetch_related('transaction_payout')

    pending_custom_filter = {
        'transaction_payout__status__in': [
            PAYOUT_STATUS.transferred,
            PAYOUT_STATUS.check_transferred
        ]
    }
    pending_query = query_set.exclude(**pending_custom_filter)

    amount = query_set.aggregate(Sum('actual_amount'))
    total_amount = float(amount['actual_amount__sum']) if amount['actual_amount__sum'] else 0
    dashboard.total_earnings = total_amount

    amount = pending_query.aggregate(Sum('actual_amount'))
    total_amount = float(amount['actual_amount__sum']) if amount['actual_amount__sum'] else 0
    dashboard.pending_payments = total_amount

    dashboard.save()


def video_data_update(dashboard):
    """
    The function will update the dashboard fields related to the video and comments
    :param dashboard:
    :return:
    """
    user = dashboard.user

    videos = StargramVideo.objects.filter(stragramz_request__celebrity_id=user.id, video__isnull=False)  # query
    comments = Comment.objects.filter(video__stragramz_request__celebrity_id=user.id)
    reactions = Reaction.objects.filter(booking__celebrity_id=user.id, file_type=FILE_TYPES.video, reaction_file__isnull=False)

    total_video_count = videos.count()  # counting
    total_comment_count = comments.count()
    total_reaction_video_count = reactions.count()

    recent_comment_count = comments.filter(created_date__gt=timezone.now()-datetime.timedelta(days=14)).count()  # recent data count
    recent_reaction_video_count = reactions.filter(created_date__gt=timezone.now() - datetime.timedelta(days=14)).count()

    dashboard.total_video_count = total_video_count  # saving in dashboard
    dashboard.total_comment_count = total_comment_count
    dashboard.total_reaction_video_count = total_reaction_video_count
    dashboard.recent_comment_count = recent_comment_count
    dashboard.recent_reaction_video_count = recent_reaction_video_count
    dashboard.save()


def rating_data_update(dashboard):
    user = dashboard.user

    recent_rating_count = FanRating.objects.filter(celebrity_id=user.id, created_date__gt=timezone.now()-datetime.timedelta(days=14)).count()
    try:
        celebrity = Celebrity.objects.get(user_id=user.id)
        rating = celebrity.rating
    except Exception:
        print('Rating of %s is not available' % user.get_short_name())
        rating = 0.00

    dashboard.recent_rating_count = recent_rating_count
    dashboard.rating = rating
    dashboard.save()


def tip_amount_update(dashboard):
    user = dashboard.user

    tip_payments = TipPayment.objects.filter(
        celebrity_id=user.id,
        created_date__gt=timezone.now()-datetime.timedelta(days=14),
        transaction_status=TIP_STATUS.captured
    )
    amount = tip_payments.aggregate(Sum('tip_payed_out'))
    recent_tip_amount = float(amount['tip_payed_out__sum']) if amount['tip_payed_out__sum'] else 0
    recent_tip_count = tip_payments.count()

    dashboard.recent_tip_count = recent_tip_count
    dashboard.recent_tip_amount = recent_tip_amount
    dashboard.save()


def booking_count_update(dashboard):
    user = dashboard.user

    requests = Stargramrequest.objects.filter(celebrity_id=user.id)

    open_booking_count = requests.filter(request_status=STATUS_TYPES.pending).count()
    thirty_days_booking_count = requests.filter(
        request_status=STATUS_TYPES.completed,
        created_date__gt=timezone.now()-datetime.timedelta(days=30)
    ).count()
    one_twenty_days_booking_count = requests.filter(
        request_status=STATUS_TYPES.completed,
        created_date__gt=timezone.now() - datetime.timedelta(days=120)
    ).count()
    one_eighty_days_booking_count = requests.filter(
        request_status=STATUS_TYPES.completed,
        created_date__gt=timezone.now() - datetime.timedelta(days=180)
    ).count()

    dashboard.open_booking_count = open_booking_count
    dashboard.thirty_days_booking_count = thirty_days_booking_count
    dashboard.one_twenty_days_booking_count = one_twenty_days_booking_count
    dashboard.one_eighty_days_booking_count = one_eighty_days_booking_count
    dashboard.save()


def biography_referral_update(dashboard):
    user = dashboard.user

    try:
        celebrity = Celebrity.object.get(user_id=user.id)
        bio = celebrity.description
        if len(bio) > 120:
            has_biography = True
        else:
            has_biography = False
    except:
        has_biography = False

    referral_count = Referral.objects.filter(referrer_id=user.id).count()
    try:
        campaign = Campaign.objects.get(id=user.referral_campaign_id)
    except Exception:
        campaign = False
    if referral_count == 0:
        has_referral = False
    elif campaign and datetime.datetime.now().date() > campaign.valid_till:
        has_referral = False
    else:
        has_referral = True

    dashboard.has_biography = has_biography
    dashboard.has_referral = has_referral
    dashboard.save()


def recent_deposit_amount(user, dashboard):
    if dashboard.last_updated_by_update_API:
        last_payment = PaymentPayout.objects.filter(
            celebrity_id=user.id,
            created_date__gt=dashboard.last_updated_by_update_API
        ).order_by('-created_date')
        if last_payment:
            amount = last_payment[0].fund_payed_out
            date = last_payment[0].created_date
        else:
            amount = 0
            date = None
        return amount, date
    else:
        return 0, None


def apply_the_checks(user, data):
    """
    Data processed for the front-end
    :param data:
    :return:
    """
    current_time = datetime.datetime.now(pytz.UTC)
    try:
        celebrity = Celebrity.objects.get(user_id=user.id)
        price = celebrity.rate
    except Exception as e:
        price = 0
        print(str(e))

    expiring_bookings = Stargramrequest.objects.filter(
        celebrity_id=user.id,
        request_status=STATUS_TYPES.pending,
        created_date__lt=timezone.now() - datetime.timedelta(days=5),
        created_date__gt=timezone.now() - datetime.timedelta(days=7)
    ).count()
    if expiring_bookings > 0:
        expiring_bookings = True
    else:
        expiring_bookings = False

    # social media promotion

    profile_share_date = data.get('last_profile_shared_at', None)
    last_video_shared_at = data.get('last_video_shared_at', None)
    if profile_share_date or last_video_shared_at:
        if profile_share_date and (current_time - profile_share_date).days < 30:
            social_promotion = True
        elif last_video_shared_at and (current_time - last_video_shared_at).days < 30:
            social_promotion = True
    else:
        social_promotion = False

    # pricing consideration calculation

    thirty_days_booking_count = data.get('thirty_days_booking_count', 0)
    one_twenty_days_booking_count = data.get('one_twenty_days_booking_count', 0)
    one_eighty_days_booking_count = data.get('one_eighty_days_booking_count', 0)
    if price > 150 and thirty_days_booking_count == 0:
        condider_pricing = True
    elif price > 100 and one_twenty_days_booking_count == 0:
        condider_pricing = True
    elif price > 50 and one_eighty_days_booking_count == 0:
        condider_pricing = True
    else:
        condider_pricing = False

    # bio check

    bio = data.get('has_biography', False)

    if bio and one_eighty_days_booking_count == 0:
        bio_check = False
    elif bio:
        bio_check = True
    else:
        bio_check = False

    data.update(
        {
            'expiring_bookings': expiring_bookings,
            'social_promotion': social_promotion,
            'condider_pricing': condider_pricing,
            'has_biography': bio_check
        }
    )

    return data
