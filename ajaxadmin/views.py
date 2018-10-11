from rest_framework.views import APIView
from utilities.mixins import ResponseViewMixin
from stargramz.models import Stargramrequest, ReportAbuse
from role.models import Role, ROLES
from ajaxadmin.serializer import StargramzAjaxSerializer
from django.core.files.storage import FileSystemStorage
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from utilities.utils import upload_image_s3, get_pre_signed_get_url, get_user_role_details
import time
import os
from config.models import Config
from django.conf import settings
from users.models import ProfileImage, StargramzUser
from django.db.models import Sum
from django.db import connection
from datetime import datetime
import urllib.request
from PIL import Image
from job.tasks import *
from stargramz.models import StargramVideo


class StargramzView(APIView, ResponseViewMixin):
    permission_classes = ()

    def get(self, request, *args, **kwargs):
        try:
            request = Stargramrequest.objects.order_by('-id')[:10]
            serializer = StargramzAjaxSerializer(request, many=True)
            return self.jp_response(s_code='HTTP_200_OK', data={'request': serializer.data})
        except Exception as e:
            return self.jp_response(s_code='HTTP_200_OK', data={'request': {}})


class WidgetView(APIView, ResponseViewMixin):
    permission_classes = ()

    def get(self, request, *args, **kwargs):
        try:

            dates = datetime.now()
            if request.GET.get('date'):
                dates = datetime.strptime(request.GET.get('date'), "%m/%d/%Y")

            current_month = dates.month
            current_year = dates.year

            users = StargramzUser.objects.all()
            user_count = users.count()

            celebrity = Role.objects.get(code=ROLES.celebrity).id
            celebrity_count = users.filter(stargramz_user__role_id=celebrity).count()
            celebrity_approved = users.filter(
                stargramz_user__role_id=celebrity,
                celebrity_user__admin_approval=True
            ).count()

            fan = Role.objects.get(code=ROLES.fan).id
            fans_count = StargramzUser.objects.filter(stargramz_user__role_id=fan).count()
            gramz = Stargramrequest.objects.all()
            abuses = ReportAbuse.objects.filter(read_flag=False).count()
            all_abuses = ReportAbuse.objects.all().count()
            total_requests = gramz.count()
            pending_request = gramz.filter(request_status__in=[2, 3]).count()
            completed_request = gramz.filter(request_status__exact=6).count()

            report = gramz.filter(created_date__month=current_month, created_date__year=current_year)
            month_request = report.count()
            month_completed_request = report.filter(request_status__exact=6).count()
            month_cancelled_request = report.filter(request_status__exact=5).count()
            month_pending_request = report.filter(request_status__in=[2, 3]).count()
            month_incomplete_request = report.filter(request_status__in=[0, 1]).count()

            total_amount = report.filter(request_transaction__transaction_status=3).aggregate(
                amount=Sum('request_transaction__amount')
            )

            refunded_amount = report.filter(request_transaction__transaction_status=5).aggregate(
                amount=Sum('request_transaction__amount')
            )

            paid_out = report.filter(request_transaction__transaction_payout__status=2).aggregate(
                amount=Sum('request_transaction__transaction_payout__fund_payed_out')
            )

            profit = report.filter(request_transaction__transaction_payout__status=2).aggregate(
                amount=Sum('request_transaction__transaction_payout__starsona_company_charges')
            )

            full_payout = gramz.filter(request_transaction__transaction_payout__status=2).aggregate(
                amount=Sum('request_transaction__transaction_payout__fund_payed_out')
            )

            full_amount = gramz.filter(request_transaction__transaction_status=3).aggregate(
                amount=Sum('request_transaction__amount')
            )

            rows = []
            with connection.cursor() as cursor:
                cursor.execute("select date_trunc('month', created_date) AS month,"
                               " sum(case when request_status = 6 then 1 else 0 end) completed,"
                               " sum(case when request_status = 5 then 1 else 0 end) cancelled"
                               " from stargramz_stargramrequest where created_date <= '%s' "
                               "group by 1 order by 1 DESC LIMIT 3" % dates)
                rows = cursor.fetchall()
                rows[:] = [[datetime.date(row[0]).strftime('%B'), row[1], row[2]] for row in reversed(rows)]

                rows = [['Month', 'Completed', 'Cancelled']] + rows

                cursor.execute("select date_trunc('month', created_date) AS month,"
                               " sum(case when users_userrolemapping.role_id = 1 then 1 else 0 end) fans,"
                               " sum(case when users_userrolemapping.role_id = 2 then 1 else 0 end) celebrities,"
                               " sum(case when users_userrolemapping.role_id = 3 then 1 else 0 end) groups"
                               " from users_stargramzuser left join users_userrolemapping on"
                               " users_stargramzuser.id=users_userrolemapping.user_id"
                               " where created_date <= '%s'"
                               " and created_date >= '%s'"
                               " group by 1 order by 1" % (dates, dates - timedelta(days=365)))
                rows2 = cursor.fetchall()
            rows2[:] = [[datetime.date(row[0]).strftime('%B')[0:3]+" "+str(datetime.date(row[0]).year)[2:4],
                         row[1], row[2], row[3]] for row in rows2]

            rows2 = [['Month', 'Fans', 'Celebrities', 'Groups']] + rows2


            return self.jp_response(
                s_code='HTTP_200_OK',
                data={
                    'total_users': user_count,
                    'total_fans': fans_count,
                    'total_celebrity': celebrity_count,
                    'total_requests': total_requests,
                    'total_abuses': abuses,
                    'all_abuses': all_abuses,
                    'pending_req': pending_request,
                    'celebrity_approved': celebrity_approved,
                    'completed_request': completed_request,
                    'report': {
                        'full_payout': full_payout.get('amount') if full_payout.get('amount') else 0,
                        'full_amount': full_amount.get('amount') if full_amount.get('amount') else 0,
                        'month_request': month_request,
                        'month_incomplete_requests': month_incomplete_request,
                        'month_completed_request': month_completed_request,
                        'month_cancelled_request': month_cancelled_request,
                        'month_pending_request': month_pending_request,
                        'total_amount': total_amount.get('amount') if total_amount.get('amount') else 0,
                        'refunded_amount': refunded_amount.get('amount') if refunded_amount.get('amount') else 0,
                        'total_paid_out': paid_out.get('amount') if paid_out.get('amount') else 0,
                        'profit': profit.get('amount') if profit.get('amount') else 0,
                        'graph': rows,
                        'graph_user': rows2
                    }
                }
            )

        except Exception:
            return self.jp_response(s_code='HTTP_200_OK', data={'request': {}})


@csrf_exempt
def upload_images(request):
    """
        Upload image to users profile and to s3.
    """
    if not request.user.is_superuser:
        return HttpResponse('Not an admin user.')
    role = get_user_role_details(request.user)
    if 'role_code' in role and role['role_code'] == 'R1006':
        return HttpResponse('Not an authorised user.')

    if request.method == 'POST' and request.FILES['image']:

        user_id = request.POST['user_id']
        img_count = int(request.POST['image_count'])
        featured = True if 'featured' in request.GET else False
        total_pics = ProfileImage.objects.filter(user_id=user_id).count()
        myfile = request.FILES['image']
        file_name, file_extension = os.path.splitext(str(myfile))

        if file_extension.lower() not in ['.jpg', '.png', '.jpeg']:
            return HttpResponse('<strong>Unsupported file format only png and jpg are allowed.</strong>')

        if total_pics < img_count:

            fs = FileSystemStorage(location='media/uploads/')
            filename = fs.save('IMG_%d%s' % (int(time.time()), file_extension), myfile)
            config = Config.objects.get(key='profile_images')
            root = settings.MEDIA_ROOT+'uploads/'

            s3file = config.value + filename
            upload_image_s3(root+filename, s3file)
            images = ProfileImage(user_id=user_id, photo=filename)
            images.save()

            if featured:
                user = StargramzUser.objects.get(id=user_id)
                user.featured_photo_id = images.id
                user.save()

            generate_thumbnail.delay()

            time.sleep(2)
            if os.path.isfile(root+filename):
                os.remove(root+filename)

            return HttpResponse('<strong>Successfully uploaded the file.</strong>')

        return HttpResponse('<strong>Maximum %d image can be uploaded for the user.</strong>' % img_count)


def delete_images(request):
    """
        Delete the image of the user.
        If primary image is deleted any of the profile image is set as primary
    """
    if not request.user.is_superuser:
        return HttpResponse('Not an admin user.')
    role = get_user_role_details(request.user)
    if 'role_code' in role and role['role_code'] == 'R1006':
        return HttpResponse('Not an authorised user.')

    user_id = request.GET['user_id']
    id = request.GET['id']
    total_pics = ProfileImage.objects.filter(user_id=user_id)

    if total_pics.count() > 1:
        try:
            user = StargramzUser.objects.get(avatar_photo_id=id)
            image = total_pics.exclude(id=id)[:1]
            user.avatar_photo_id = image[0].id
            user.save()
        except Exception:
            pass
        ProfileImage.objects.filter(id=id).delete()
        return HttpResponse('Successfully deleted the image.')

    return HttpResponse('Image cannot be deleted minimum one image is required', status=400)


@csrf_exempt
def crop_images(request):
    """
        Crop the image and upload to s3
    """
    role = get_user_role_details(request.user)
    if 'role_code' in role and role['role_code'] == 'R1006':
        return HttpResponse('Not an authorised user.')

    if not request.user.is_superuser:
        return HttpResponse('Not an admin user.')

    if request.POST['profile_id']:
        pk = request.POST['profile_id']
        try:
            image = ProfileImage.objects.get(pk=pk)
            filename = image.photo
            config = Config.objects.get(key='profile_images')
            your_media_root = settings.MEDIA_ROOT + 'thumbnails/'
            s3folder = config.value

            img_url = get_pre_signed_get_url(filename, s3folder)
            image_original = your_media_root + filename

            try:
                # Downloading the image from s3
                urllib.request.urlretrieve(img_url, image_original)
            except Exception:
                return HttpResponse('Image cropping failed')

            x1 = round(float(request.POST['x1']), 2)
            y1 = round(float(request.POST['y1']), 2)
            x2 = round(float(request.POST['x2']), 2)
            y2 = round(float(request.POST['y2']), 2)

            coords = (x1, y1, x2, y2)

            cropped = Image.open(image_original)
            cropped = cropped.crop(coords)
            cropped.save(image_original, quality=99, optimize=True)

            s3file = config.value + filename
            upload_image_s3(your_media_root + filename, s3file)
            image.thumbnail = None
            image.save()
            generate_thumbnail.delay()

            time.sleep(2)
            if os.path.isfile(your_media_root + filename):
                os.remove(your_media_root + filename)

        except Exception:
            return HttpResponse('Image cropping failed')
        return HttpResponse('Image has been cropped and uploaded successfully')
    else:
        return HttpResponse('Image cropping failed')


@csrf_exempt
def crop_featured_image(request):
    """
        Crop the image and upload to s3
    """
    if not request.user.is_superuser:
        return HttpResponse('Not an admin user.')
    role = get_user_role_details(request.user)
    if 'role_code' in role and role['role_code'] == 'R1006':
        return HttpResponse('Not an authorised user.')

    if request.POST['featured_id']:
        pk = request.POST['featured_id']
        try:
            image = ProfileImage.objects.get(pk=pk)
            filename = image.photo
            config = Config.objects.get(key='profile_images')
            your_media_root = settings.MEDIA_ROOT + 'thumbnails/'
            s3folder = config.value

            img_url = get_pre_signed_get_url(filename, s3folder)
            image_original = your_media_root + filename

            try:
                # Downloading the image from s3
                urllib.request.urlretrieve(img_url, image_original)
            except Exception:
                return HttpResponse('Image cropping failed')

            x1 = round(float(request.POST['x1f']), 2)
            y1 = round(float(request.POST['y1f']), 2)
            x2 = round(float(request.POST['x2f']), 2)
            y2 = round(float(request.POST['y2f']), 2)

            coords = (x1, y1, x2, y2)

            cropped = Image.open(image_original)
            cropped = cropped.crop(coords)
            cropped.save(image_original, quality=99, optimize=True)

            s3file = config.value + filename
            upload_image_s3(your_media_root + filename, s3file)
            image.thumbnail = None
            image.save()
            generate_thumbnail.delay()

            time.sleep(2)
            if os.path.isfile(your_media_root + filename):
                os.remove(your_media_root + filename)

        except Exception:
            return HttpResponse('Image cropping failed')
        return HttpResponse('Image has been cropped and uploaded successfully')
    else:
        return HttpResponse('Image cropping failed')



@csrf_exempt
def avatar_image(request):
    """
        Update the Avatar image of the user
    """

    if not request.user.is_superuser:
        return HttpResponse('Not an admin user.')
    role = get_user_role_details(request.user)
    if 'role_code' in role and role['role_code'] == 'R1006':
        return HttpResponse('Not an authorised user.')

    if request.POST['profile_image'] and request.POST['user_id']:

        try:
            user = StargramzUser.objects.get(id=request.POST['user_id'])
            user.avatar_photo_id = request.POST['profile_image']
            user.save()
        except Exception:
            return HttpResponse('Avatar image not updated.')
        return HttpResponse('Avatar image has been updated')
    else:
        return HttpResponse('Avatar image not updated.')


def run_process(request):

    if not request.user.is_superuser:
        return HttpResponse('Not an admin user.')
    role = get_user_role_details(request.user)
    if 'role_code' in role and role['role_code'] == 'R1006':
        return HttpResponse('Not authorised.')

    if request.GET['process']:
        process = request.GET['process']

        if process == 'create_payout_records':
            create_payout_records.delay()
        if process == 'generate_video_thumbnail':
            generate_video_thumbnail.delay()
        if process == 'generate_thumbnail':
            generate_thumbnail.delay()

    return HttpResponse("Welcome")


def process_booking(request):
    """
    Complete the booking request process
    :param request:
    :return:
    """
    if not request.user.is_superuser:
        return HttpResponse('Not an admin user.')
    role = get_user_role_details(request.user)
    if 'role_code' in role and role['role_code'] == 'R1006':
        return HttpResponse('Not authorised.')
    booking_id = request.GET.get('booking')

    try:
        booking_details = Stargramrequest.objects.get(id=booking_id)
        if booking_details.request_type == 3:
            combine_video_clips.delay(booking_id)
            return HttpResponse("Added video for processing.")
        else:
            try:
                video_ids = StargramVideo.objects.values_list('id', flat=True).filter(stragramz_request_id=booking_id)
                for video_id in video_ids:
                    generate_video_thumbnail.delay(id=video_id)
                return HttpResponse("Added video for processing.")
            except Exception as e:
                return HttpResponse(str(e))
    except Exception as e:
        return HttpResponse("No booking Id found %s" % str(e))
