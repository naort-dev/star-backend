from django.template.loader import get_template
from rest_framework.views import APIView
from utilities.mixins import ResponseViewMixin
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from .models import StargramzUser, Celebrity, UserRoleMapping, Role, CelebrityProfession
from config.models import Config
from .serializer import CelebrityProfileSerializer, CelebrityProfessionSerializer
from utilities.utils import removefromdict, ROLES
from utilities.permissions import CustomPermission
from utilities.utils import SendMail
from utilities.constants import BASE_URL
from stargramz.models import StargramVideo
from stargramz.serializer import StargramzVideoSerializer
from .tasks import alert_admin_celebrity_updates, welcome_email


class CelebrityManagement(APIView, ResponseViewMixin):

    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)

    def post(self, request):
        """
            Celebrity details Add
        """
        try:
            user = StargramzUser.objects.get(username=request.user)
        except StargramzUser.DoesNotExist:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_SIGNUP', 'Invalid Signup User')

        try:
            celebrity = Celebrity.objects.get(user=user)
        except Exception:
            request.data['user'] = user.id
            fields = ['user']
            field_list = ['profession', 'rate', 'weekly_limits', 'availability',
                          'profile_video', 'description', 'charity']
            for list_item in field_list:
                if list_item in request.data:
                    fields.append(list_item)
            serializer = CelebrityProfileSerializer(data=request.data, instance=None,
                                                    fields=fields)
            if serializer.is_valid():
                celebrity = serializer.save()
                try:
                    role_id = Role.objects.get(code=ROLES.celebrity).id
                except Exception:
                    role_id = ROLES.celebrity
                roles_mapping = UserRoleMapping.objects.get(user=user)
                if roles_mapping.role.code == ROLES.fan:
                    celebrity.has_fan_account = True
                    celebrity.save()
                roles_mapping.is_complete = True
                roles_mapping.role_id = role_id
                roles_mapping.save()
                welcome_email.delay(celebrity.user.id)
                alert_admin_celebrity_updates.delay(celebrity.user.id, 1)
            else:
                return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_LOGIN',
                                              self.error_msg_string(serializer.errors))

        if celebrity:
            data = CelebrityProfileSerializer(celebrity).data
            keys = ['user', 'created_date', 'profile_video', 'id']
            data = removefromdict(data, keys)
            celebrity_professions = CelebrityProfession.objects.filter(user=user)
            celebrity_data = CelebrityProfessionSerializer(celebrity_professions, many=True).data
            data['profession_details'] = celebrity_data
        return self.jp_response('HTTP_200_OK', data={'celebrity': data})

    def update_celebrity(self, request, pk):
        """
            Celebrity details Update
        """
        return_data = dict()
        try:
            celebrity = Celebrity.objects.get(user_id=pk)
        except Celebrity.DoesNotExist:
            return_data = dict(status='HTTP_500_INTERNAL_SERVER_ERROR', e_code='INVALID_USER',
                               message='Invalid user details')
            return return_data
        fields = []
        field_list = ['profession', 'rate', 'weekly_limits', 'availability', 'description', 'charity', 'check_payments']
        for list_item in field_list:
            if list_item in request:
                fields.append(list_item)
        serializer = CelebrityProfileSerializer(data=request, instance=celebrity, fields=fields)
        if serializer.is_valid():
            celebrity = serializer.save()
            if celebrity:
                data = CelebrityProfileSerializer(celebrity).data
                celebrity_professions = CelebrityProfession.objects.filter(user_id=pk)
                celebrity_data = CelebrityProfessionSerializer(celebrity_professions, many=True).data
                data['profession_details'] = celebrity_data
                keys = ['id', 'user', 'created_date', 'profile_video']
                data = removefromdict(data, keys)
                return_data = dict(status='HTTP_200_OK', data={'celebrity': data}, content_type='application/json')
        else:
            return_data = dict(status='HTTP_400_BAD_REQUEST', e_code='INVALID_CODE',
                               message=self.error_msg_string(serializer.errors))
        return return_data

    def retrieve_celebrity(self, pk):
        """
             Celebrity details Retrieve
        """
        try:
            celebrity = Celebrity.objects.get(user_id=pk)
        except Celebrity.DoesNotExist:
            return dict(status='HTTP_400_BAD_REQUEST', e_code='INVALID_USER', message='Invalid user details')
        if celebrity:
            data = CelebrityProfileSerializer(
                celebrity, fields=['rating', 'weekly_limits', 'featured', 'rating', 'remaining_limit', 'profession',
                                   'profession_name', 'charity', 'description', 'follow_count', 'rate',
                                   'availability', 'stripe_user_id', 'pending_requests_count', 'check_payments']).data
            celebrity_professions = CelebrityProfession.objects.filter(user_id=pk).select_related('profession')
            videos = StargramVideo.objects.filter(
                stragramz_request__celebrity__id=pk,
                stragramz_request__request_status=6,
                stragramz_request__public_request=True
            ).order_by('-stragramz_request__id')\
            .select_related('stragramz_request')\
            .prefetch_related('stragramz_request__celebrity', 'stragramz_request__occasion')[:20]
            related_starsona_videos = StargramzVideoSerializer(
                videos, many=True, fields=['s3_video_url', 's3_thumbnail_url','video_url',
                                           'video_status', 'first_name', 'last_name', 'occasion',
                                           'booking_id', 'booking_type', 'width', 'height']).data
            booking_videos = dict()
            videos = []
            for video in related_starsona_videos:
                if video['booking_id'] in booking_videos:
                    booking_videos[video['booking_id']].append(video)
                else:
                    booking_videos[video['booking_id']] = [video]

            for key, values in sorted(booking_videos.items()):
                videos.append({'videos': values})
            videos.reverse()
            related_videos = videos[:10]

            # Need to remove the related video as related videos are loaded from Featured videos API
            data['related_videos'] = related_videos
            celebrity_data = CelebrityProfessionSerializer(celebrity_professions, many=True).data
            data['profession_details'] = celebrity_data
            return dict(status='HTTP_200_OK', data={'celebrity': data}, content_type='application/json')


class NotifyAdmin(APIView, ResponseViewMixin):
    """
        Send notification email to Admin
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)

    def get(self, request, *args, **kwargs):

        user = StargramzUser.objects.get(username=request.user)
        config_email = Config.objects.get(key='sender_email').value

        ctx = {
            'celebrity_name': user.first_name+" "+user.last_name,
            'base_url': BASE_URL,
        }

        html_template = get_template('../templates/emails/starsona_email.html')
        html_content = html_template.render(ctx)
        mail_status = SendMail('Starsona Video Request', html_content, sender_email=config_email, to=config_email)
        if mail_status:
            return self.jp_response(s_code='HTTP_200_OK', data='Successfully notified')
        else:
            return self.jp_error_response('HTTP_502_BAD_GATEWAY', 'UNKNOWN_QUERY',
                                          'Email was not send due to temperory errors')
