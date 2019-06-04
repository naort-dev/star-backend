from django.template.loader import get_template
from rest_framework.views import APIView
from utilities.mixins import ResponseViewMixin
from rest_framework.viewsets import GenericViewSet
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from utilities.pagination import CustomOffsetPagination
from .models import StargramzUser, Celebrity, UserRoleMapping, Role, CelebrityProfession, Campaign, Representative,\
    AdminReferral
from config.models import Config
from .serializer import CelebrityProfileSerializer, CelebrityProfessionSerializer, ReferralUserSerializer, \
    CelebrityRepresentativeSerializer, CelebrityRepresentativeViewSerializer
from utilities.utils import removefromdict, ROLES, decode_pk, encode_pk
from utilities.permissions import CustomPermission
from utilities.utils import SendMail
from utilities.constants import BASE_URL
from stargramz.models import StargramVideo
from stargramz.serializer import StargramzVideoSerializer
from .tasks import alert_admin_celebrity_updates, welcome_email
from versioned.v2.users.tasks import remove_existing_profile_video_from_s3


class CelebrityManagement(APIView, ResponseViewMixin):

    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)

    welcome_mail = welcome_email

    def post(self, request):
        """
            Celebrity details Add
        """
        user = request.user

        try:
            celebrity = Celebrity.objects.get(user=user)
            celebrity_update = True
        except Exception:
            celebrity = None
            celebrity_update = False
        request.data['user'] = user.id
        fields = ['user']
        field_list = ['profession', 'rate', 'in_app_price', 'weekly_limits', 'availability',
                      'profile_video', 'description', 'charity']
        for list_item in field_list:
            if list_item in request.data:
                fields.append(list_item)
        not_recordable = request.data.get('recordable', None)
        not_recordable = True if not_recordable == 'false' else None
        serializer = CelebrityProfileSerializer(data=request.data, instance=celebrity,
                                                fields=fields)
        if serializer.is_valid():
            if celebrity_update and request.data.get('profile_video', '') != '':
                remove_existing_profile_video_from_s3.delay(celebrity.id)
            celebrity = serializer.save()
            try:
                role_id = Role.objects.get(code=ROLES.celebrity).id
            except Exception:
                role_id = ROLES.celebrity
            roles_mapping = UserRoleMapping.objects.get(user=user)
            if roles_mapping.role.code == ROLES.fan:
                celebrity.has_fan_account = True
            # Celebrity approval by default
            if user.admin_approval_referral_code and user.admin_approval_referral_code.activate:
                celebrity.admin_approval = True
            celebrity.save()
            roles_mapping.is_complete = True
            roles_mapping.role_id = role_id
            roles_mapping.save()
            if not celebrity_update:
                self.welcome_mail.delay(celebrity.user.id, not_recordable)
                alert_admin_celebrity_updates.delay(celebrity.user.id, 1)
        else:
            return self.jp_error_response(
                'HTTP_400_BAD_REQUEST', 'INVALID_LOGIN', self.error_msg_string(serializer.errors)
            )

        if celebrity:
            data = CelebrityProfileSerializer(celebrity).data
            keys = ['user', 'created_date', 'profile_video', 'id', 'migrated', 'star_approved']
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
        # Remove 'check_payments' after next app release
        field_list = ['profession', 'rate', 'weekly_limits', 'in_app_price', 'availability', 'description', 'charity', 'check_payments', 'profile_video']
        for list_item in field_list:
            if list_item in request:
                fields.append(list_item)
        if 'in_app_price' not in request:
            fields.append('in_app_price')
            request.update({"in_app_price": None})
        if 'profile_video' in request and request.get('profile_video', '') != '':
            remove_existing_profile_video_from_s3.delay(celebrity.id)
        serializer = CelebrityProfileSerializer(data=request, instance=celebrity, fields=fields)
        if serializer.is_valid():
            celebrity = serializer.save()
            if celebrity:
                data = CelebrityProfileSerializer(celebrity).data
                celebrity_professions = CelebrityProfession.objects.filter(user_id=pk)
                celebrity_data = CelebrityProfessionSerializer(celebrity_professions, many=True).data
                data['profession_details'] = celebrity_data
                keys = ['id', 'user', 'created_date', 'profile_video']
                in_app_price_limit(data)
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
                # Remove 'check_payments' from celebrity after next app release
                celebrity, fields=['rating', 'weekly_limits', 'featured', 'remaining_limit', 'profession',
                                   'profession_name', 'charity', 'description', 'follow_count', 'rate', 'in_app_price',
                                   'availability', 'stripe_user_id', 'pending_requests_count', 'check_payments'
                                   ]).data
            in_app_price_limit(data)
            celebrity_professions = CelebrityProfession.objects.filter(user_id=pk).select_related('profession')
            data['related_videos'] = []
            celebrity_data = CelebrityProfessionSerializer(celebrity_professions, many=True).data
            data['profession_details'] = celebrity_data
            return dict(status='HTTP_200_OK', data={'celebrity': data}, content_type='application/json')


def in_app_price_limit(data):
    in_app_price = data.get("in_app_price")
    rate = int(float(data.get("rate", "0.00")))
    if not in_app_price:
        in_app_price = rate
    elif rate > 1000:
        in_app_price = rate
    data.update({"in_app_price": str(in_app_price)})


class NotifyAdmin(APIView, ResponseViewMixin):
    """
        Send notification email to Admin
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)

    def get(self, request, *args, **kwargs):

        config_email = Config.objects.get(key='sender_email').value

        ctx = {
            'celebrity_name': request.user.get_short_name(),
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


class ReferralRequest(APIView, ResponseViewMixin):
    """
        Send email notification to admin to request the referral activation
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)

    def post(self, request):
        try:
            user = request.user

            config_email = Config.objects.get(key='sender_email').value

            ctx = {
                'celebrity_name': user.get_short_name(),
                'base_url': BASE_URL,
            }

            html_template = get_template('../templates/emails/referral_activation.html')
            html_content = html_template.render(ctx)
            mail_status = SendMail('Starsona Referral Activation', html_content, sender_email=config_email, to=config_email)
            if mail_status:
                try:
                    user.has_requested_referral = True
                    user.save()
                except Exception as e:
                    pass

                return self.jp_response(s_code='HTTP_200_OK', data={'message': 'Successfully notified'})
            else:
                return self.jp_error_response('HTTP_502_BAD_GATEWAY', 'UNKNOWN_QUERY',
                                              'Email was not send due to temperory errors')
        except StargramzUser.DoesNotExist:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_SIGNUP', 'Invalid Signup User')


class ReferralList(GenericViewSet, ResponseViewMixin):
    """
        The list of celebrities and celebrity search
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)
    pagination_class = CustomOffsetPagination
    serializer_class = ReferralUserSerializer

    def list(self, request):
        user = StargramzUser.objects.get(username=request.user)
        query_set = StargramzUser.objects.filter(refer_referee__referrer_id=user.id)
        page = self.paginate_queryset(query_set)
        serializer = self.get_serializer(page, many=True)
        return self.paginator.get_paginated_response(serializer.data, key_name='referral_list')


class ReferralValidate(APIView, ResponseViewMixin):
    """
        Validate the Referral promo code is valid with to celebrities
    """
    authentication_classes = ()
    permission_classes = (CustomPermission,)

    def post(self, request):
        try:
            referral_code = request.data.get('referral_code').upper() if request.data.get('referral_code', None) else None
            if AdminReferral.objects.filter(referral_code=referral_code, activate=True).count() > 0:
                return self.jp_response(s_code='HTTP_200_OK', data={'message': 'Valid promo code'})
            StargramzUser.objects.values_list('id', flat=True).get(referral_code=referral_code, referral_active=True)
            return self.jp_response(s_code='HTTP_200_OK', data={'message': 'Valid promo code'})
        except StargramzUser.DoesNotExist:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'EXCEPTION', 'Invalid Promo code')


class CelebrityRepresentative(APIView, ResponseViewMixin):

    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)

    def post(self, request, pk):
        request.data['celebrity'] = request.user.id
        if pk:
            try:
                representative_id = decode_pk(pk)
                representative = Representative.objects.get(id=representative_id)
                if not request.data.get('email'):
                    del request.data['email']
                serializer = CelebrityRepresentativeSerializer(data=request.data, instance=representative)
                if serializer.is_valid():
                    serializer.save()
                    return self.jp_response(s_code='HTTP_200_OK', data={'message': 'Successfully updated'})
                else:
                    return self.jp_error_response(
                        'HTTP_400_BAD_REQUEST', 'EXCEPTION', self.error_msg_string(serializer.errors)
                    )
            except Exception:
                return self.jp_error_response('HTTP_400_BAD_REQUEST', 'EXCEPTION', 'invalid id')
        else:
            serializer = CelebrityRepresentativeSerializer(data=request.data, instance=None)
            if serializer.is_valid():
                try:
                    data = serializer.save()
                    representative_id = encode_pk(data.id)
                except Exception as e:
                    return self.jp_error_response(
                        'HTTP_400_BAD_REQUEST', 'EXCEPTION', e.args[0]
                    )
                return self.jp_response(
                    s_code='HTTP_200_OK',
                    data={'message': 'Successfully inserted', 'representative_id': representative_id}
                )
            else:
                return self.jp_error_response(
                    'HTTP_400_BAD_REQUEST', 'EXCEPTION', self.error_msg_string(serializer.errors)
                )

    def get(self, request, pk):
        representative = Representative.objects.filter(celebrity=request.user)
        serializer = CelebrityRepresentativeViewSerializer(representative, many=True)
        return self.jp_response(s_code='HTTP_200_OK', data={"representatives": serializer.data})

    def delete(self, request, pk):
        try:
            representative = decode_pk(pk)
            Representative.objects.filter(celebrity=request.user, id=representative).delete()
        except Exception:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'EXCEPTION', 'invalid id')
        return self.jp_response(s_code='HTTP_200_OK', data={'message': 'Successfully deleted'})


def celebrity_representative_email_verification(request, rep_id):
    from django.http import HttpResponseRedirect
    web_url = Config.objects.get(key='web_url').value
    try:
        representative_id = decode_pk(rep_id)
        representative = Representative.objects.get(id=representative_id)
        representative.email_verified = True
        representative.save()
    except Exception:
        return HttpResponseRedirect(web_url)
    return HttpResponseRedirect(web_url)
