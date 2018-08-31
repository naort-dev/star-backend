from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView
from utilities.mixins import ResponseViewMixin
from users.serializer import *
from users.models import StargramzUser, Profession, CelebrityFollow, CelebrityView, DeviceTokens, \
    CelebrityAvailableAlert
from utilities.utils import SendMail, get_user_role_details, ROLES, check_user_role, change_fcm_device_status, \
    check_celebrity_profile_exist, generate_branch_io_url, get_pre_signed_post_url
from django.template.loader import get_template
import uuid
from users.constants import EMAIL_HOST_USER
from django.utils import timezone
from config.constants import *
from config.models import Config
from rest_framework import viewsets
from rest_framework.viewsets import GenericViewSet
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from .models import NOTIFICATION_TYPES
from .celebrity_views import CelebrityManagement
from rest_framework import status
from django.db import transaction
from role.models import Role
from django.core.exceptions import ValidationError
from .constants import CELEBRITY_CODE, ROLE_ERROR_CODE, EMAIL_ERROR_CODE, FIRST_NAME_ERROR_CODE
from job.tasks import generate_thumbnail
from rest_framework.decorators import detail_route
from utilities.permissions import CustomPermission
from utilities.constants import REDIRECT_LINK, BASE_URL
from hashids import Hashids
from .utils import generate_random_code
import time
hashids = Hashids(min_length=8)


class UserRegister(APIView, ResponseViewMixin):
    """
        Register user
    """
    def post(self, request, *args):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            if user:
                data = serializer.validated_data
                user = StargramzUser.objects.get(username=data['email'])
                role_details = get_user_role_details(user)
                data = RegisterSerializer(user).data
                (token, created) = Token.objects.get_or_create(user=user)
                data['authentication_token'] = token.key
                (notifications, created) = SettingsNotifications.objects.get_or_create(user_id=user.id)
                data['notification_settings'] = NotificationSettingsSerializer(notifications).data
                data['role_details'] = role_details
                return self.jp_response(s_code='HTTP_200_OK', data={'user': data})
            else:
                return self.jp_error_response('HTTP_500_INTERNAL_SERVER_ERROR', 'EXCEPTION', '')
        else:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_CREATE',
                                          self.error_msg_string(serializer.errors))


class UserLogin(APIView, ResponseViewMixin):

    def post(self, request, *args, **kwargs):
        """
            User Login
        """
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.data
            user = StargramzUser.objects.get(email=data['email'])
            user = StargramzUser.objects.get(username=data['email'])
            role_details = get_user_role_details(user)
            serializer = LoginSerializer(data)
            response_data = {'user': data}
            data['role_details'] = role_details
            data['celebrity'] = check_celebrity_profile_exist(user)

            (notifications, created) = SettingsNotifications.objects.get_or_create(user_id=user.id)
            data['notification_settings'] = NotificationSettingsSerializer(notifications).data
            if check_user_role(user, ROLES.celebrity) and data['role_details']['is_complete']:
                celebrity_details = CelebrityManagement.retrieve_celebrity(self, user.id)
                if getattr(status, celebrity_details['status']) == 200:
                    response_data['celebrity_details'] = celebrity_details['data']['celebrity']
                else:
                    return self.jp_error_response('HTTP_400_BAD_REQUEST', celebrity_details['e_code'],
                                                  celebrity_details['message'])
            return self.jp_response(s_code='HTTP_200_OK', data=response_data)
        else:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_LOGIN',
                                          self.error_msg_string(serializer.errors))


class EmailValidate(APIView, ResponseViewMixin):

    def post(self, request):
        """
            Validate Email Address
        """
        serializer = EmailSerializer(data=request.data)
        if serializer.is_valid():
            return self.jp_response(s_code='HTTP_200_OK')
        else:
            return self.jp_error_response(
                'HTTP_400_BAD_REQUEST',
                'USER_EXISTS',
                'Email already registered')


class SocialSignup(APIView, ResponseViewMixin):

    def post(self, request):
        """
            Social Sign up
        """
        serializer = SocialSignupSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            if type(user) is dict:
                if user['code'] == ROLE_ERROR_CODE:
                    return self.jp_error_response('HTTP_200_OK', 'INVALID_CREATE',
                                                  user['message'], str(user['code']))
                if user['code'] == EMAIL_ERROR_CODE:
                    return self.jp_error_response('HTTP_200_OK', 'INVALID_CREATE',
                                                  user['message'], str(user['code']))
                if user['code'] == FIRST_NAME_ERROR_CODE:
                    return self.jp_error_response('HTTP_200_OK', 'INVALID_CREATE',
                                                  user['message'], str(user['code']))
            if user:
                user = StargramzUser.objects.get(username=user.username)
                role_details = get_user_role_details(user)
                data = RegisterSerializer(user).data
                (token, created) = Token.objects.get_or_create(user=user)
                response_data = {'user': data}
                data['authentication_token'] = token.key
                data['role_details'] = role_details
                data['celebrity'] = check_celebrity_profile_exist(user)
                (notifications, created) = SettingsNotifications.objects.get_or_create(user_id=user.id)
                data['notification_settings'] = NotificationSettingsSerializer(notifications).data
                if check_user_role(user, ROLES.celebrity) and data['role_details']['is_complete']:
                    celebrity_details = CelebrityManagement.retrieve_celebrity(self, user.id)
                    if getattr(status, celebrity_details['status']) == 200:
                        response_data['celebrity_details'] = celebrity_details['data']['celebrity']
                    else:
                        return self.jp_error_response('HTTP_400_BAD_REQUEST', celebrity_details['e_code'],
                                                      celebrity_details['message'])
                return self.jp_response(s_code='HTTP_200_OK', data=response_data)
            else:
                return self.jp_error_response('HTTP_500_INTERNAL_SERVER_ERROR', 'EXCEPTION', '')
        else:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_CREATE',
                                          self.error_msg_string(serializer.errors))


class UserLogout(APIView, ResponseViewMixin):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)

    def post(self, request, *args, **kwargs):
        """
            User Logout
        """
        user = request.user
        change_fcm_device_status(user, False, request.data['registration_id'])
        # Token.objects.filter(user=user).delete()

        return self.jp_response(data={'logout': True})


class ForgotPassword(APIView, ResponseViewMixin):

    def post(self, request):
        """
            Forgot Password
        """
        serializer = ForgotPasswordSerializer(data=request.data)
        if serializer.is_valid():
            try:
                user = StargramzUser.objects.get(username=serializer.data['email'])
                user.reset_id = uuid.uuid4()
                user.reset_generate_time = timezone.now()
                user.save()
            except StargramzUser.DoesNotExist:
                return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_USER',
                                              'Email is not registered with Starsona.')
            subject = 'Starsona Password Reset'

            try:
                config_email = Config.objects.get(key='sender_email').value
            except Config.DoesNotExist:
                config_email = EMAIL_HOST_USER

            try:
                reset_password_link = Config.objects.get(key='reset_password_link').value
            except Config.DoesNotExist:
                reset_password_link = REDIRECT_LINK

            try:
                website_link = Config.objects.get(key='web_url').value
            except Config.DoesNotExist:
                website_link = BASE_URL

            try:
                base_url = Config.objects.get(key='base_url').value
            except Config.DoesNotExist:
                base_url = BASE_URL

            web_reset_url = "%s%s%s" % (website_link, 'resetpassword?reset_id=',str(user.reset_id))

            ctx = {
                'base_url': base_url,
                'username': user.first_name + ' ' + user.last_name,
                'reset_link': generate_branch_io_url(
                    mob_url='reset/?reset_id=%s' % str(user.reset_id),
                    title="Reset password for %s" % user.get_short_name(),
                    desc="Reset password for %s" % user.get_short_name(),
                    image_url='%smedia/web-images/starsona_logo.png' % base_url,
                    desktop_url=web_reset_url,
                    canonical_url=reset_password_link+str(user.reset_id),
                )
            }

            html_template = get_template('../templates/emails/forgot_password.html')
            html_content = html_template.render(ctx)
            mail_status = SendMail(subject, html_content, sender_email=config_email, to=user.username)
            if mail_status:
                return self.jp_response(s_code='HTTP_200_OK', data='Mail has been sent to given email address')
            else:
                return self.jp_error_response('HTTP_502_BAD_GATEWAY', 'UNKNOWN_QUERY',
                                              'Email was not send due to temperory errors')
        else:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_CODE', 'Invalid Email Address')


class ResetPassword(APIView, ResponseViewMixin):

    def post(self, request):
        """
            Reset Password
        """
        serializer = ResetPasswordSerializer(data=request.data)
        data = dict()
        if serializer.is_valid():
            password = serializer.data['password']
            user = StargramzUser.objects.get(reset_id=serializer.data['reset_id'])
            user.set_password(password)
            user.reset_id = None
            user.reset_generate_time = None
            user.save()
            Token.objects.filter(user=user).delete()
            (token, created) = Token.objects.get_or_create(user=user)
            data['authentication_token'] = token.key
            data['id'] = user.id
            return self.jp_response(s_code='HTTP_200_OK', data={"details": data})
        else:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_CODE',
                                          self.error_msg_string(serializer.errors))


class ChangePassword(APIView, ResponseViewMixin):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)

    def post(self, request):
        """
            Change the password
        """
        try:
            user = StargramzUser.objects.get(username=request.user)
        except StargramzUser.DoesNotExist:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_UPDATE', ['User not found'])
        serializer = ChangePasswordSerializer(data=request.data, context={'user': user})
        if serializer.is_valid():
            user.set_password(request.data['new_password'])
            user.save()
            return self.jp_response(s_code='HTTP_200_OK', data='Password has been updated successfully')
        else:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_UPDATE',
                                          self.error_msg_string(serializer.errors))


class Professions(APIView, ResponseViewMixin):
    """
        Get all the Professions for Celebrities
    """
    def get(self, request, *args, **kwargs):
        profession = Profession.objects.filter(parent=None)
        profession_data = ProfessionSerializer(profession, many=True)
        return self.jp_response(s_code='HTTP_200_OK', data={'professions': profession_data.data})


class FilterProfessions(GenericViewSet, ResponseViewMixin):
    """
        Get the filtered list of Profession
    """
    def list(self, request):
        #query_set = CelebrityProfession.objects.filter(profession__parent__isnull=False).values_list('profession', flat=True).distinct()
        query_set = CelebrityProfession.objects.all().distinct()
        parent_null = query_set.filter(profession__parent__isnull=False).values_list('profession__parent', flat=True)
        parent_not_null = query_set.filter(profession__parent__isnull=True).values_list('profession', flat=True)
        parent_null.union(parent_not_null)
        profession = Profession.objects.filter(id__in=parent_null, parent__isnull=True)
        profession_data = ProfessionFilterSerializer(profession, many=True)
        return self.jp_response(s_code='HTTP_200_OK', data={'filtered-professions': profession_data.data})


class ProfileImages(GenericAPIView, ResponseViewMixin):
    """
        Profile Images
    """
    queryset = StargramzUser.objects.all()
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)

    def post(self, request, *args, **kwargs):
        try:
            user = request.data['user'] = StargramzUser.objects.get(username=request.user)
        except Exception as e:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_UPDATE', ['User not found'])
        images = request.data['images']
        avatar_image = featured_image = None
        default_avatar_image = request.data['images'][0]
        input_data = {"images_list": [{"photo": item} for item in images]}
        if 'avatar_photo' in request.data:
            avatar_image = request.data['avatar_photo']
            input_data['avatar_photo'] = avatar_image
        if 'featured_image' in request.data:
            featured_image = request.data['featured_image']
            input_data['featured_image'] = featured_image
        # Fix for iOS need to remove featured_photo in next release #remove
        if 'featured_photo' in request.data:
            featured_image = request.data['featured_photo']
            input_data['featured_image'] = featured_image
        serializer = ProfileImageSerializer(data=input_data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            user.featured_photo_id = ProfileImage.objects.get(photo=featured_image, user=user).id if featured_image else \
                None
            user.avatar_photo_id = ProfileImage.objects.get(photo=avatar_image, user=user).id if avatar_image else \
                ProfileImage.objects.get(photo=default_avatar_image, user=user).id
            user.save()
            generate_thumbnail.delay()
            return self.jp_response(s_code='HTTP_200_OK', data={'request': 'Successfully updated images'})
        else:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_UPDATE',
                                          self.error_msg_string(serializer.errors))


class RemoveProfileImage(APIView, ResponseViewMixin):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)

    def post(self, request):
        try:
            user = StargramzUser.objects.get(username=request.user)
        except StargramzUser.DoesNotExist:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_UPDATE', ['User not found'])

        serializer = ImageRemoveSerializer(data=request.data)
        if serializer.is_valid():
            if str(user.avatar_photo_id) in request.data['id']:
                user.avatar_photo_id = None
                user.save()
            ProfileImage.objects.filter(Q(user=user) & Q(id__in=request.data['id'])).delete()
            return self.jp_response(s_code='HTTP_200_OK', data={'request': 'Successfully Removed images'})
        else:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_UPDATE',
                                          self.error_msg_list(serializer.errors))


class NotificationSettings(APIView, ResponseViewMixin):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)

    def post(self, request):
        field_defaults = {}
        try:
            user = StargramzUser.objects.get(username=request.user)
            request.data['user'] = user.id
        except StargramzUser.DoesNotExist:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_UPDATE', ['User not found'])
        notification_keys = NOTIFICATION_TYPES.get_keys()
        # For getting the fields to update
        fields = [list_item for list_item in notification_keys if list_item in request.data]
        if not fields:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_UPDATE',
                                          'No valid notification types where provided')
        fields.append('user')
        serializer = NotificationSettingsSerializer(data=request.data, fields=fields)
        if serializer.is_valid():
            # Setting the fields to add in defaults
            for field in fields:
                field_defaults[field] = serializer.validated_data.get(field)
            notifications, created = SettingsNotifications.objects.update_or_create(user_id=user.id,
                                                                                    defaults=field_defaults)
            data = NotificationSettingsSerializer(notifications).data
            return self.jp_response(s_code='HTTP_200_OK', data={'notification_settings': data})
        else:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_UPDATE',
                                          self.error_msg_list(serializer.errors))


class UserDetails(viewsets.ViewSet, ResponseViewMixin):
    """
        Update and Retrieve User Details
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)

    @detail_route(methods=['get'], permission_classes=[CustomPermission], authentication_classes=[])
    def get_details(self, request, pk=None, user_followed=None, user_logged_in=None):

        try:
            pk = self.verify_hash_token(pk)
            pk = int(pk)
        except Exception:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_SIGNUP', 'User Does not Exist')
        try:
            user = StargramzUser.objects.get(id=pk)
        except StargramzUser.DoesNotExist:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_SIGNUP', 'User Does not Exist')

        celebrity = check_celebrity_profile_exist(user)
        if not celebrity and user_logged_in != user.id:
            return self.jp_error_response('HTTP_403_FORBIDDEN', 'INVALID_USER', 'Not an authorized user.')

        data = RegisterSerializer(user, context={'request': request}).data
        try:
            vanity_url = VanityUrl.objects.values_list('name', flat=True).get(user_id=user.id)
        except Exception:
            vanity_url = ''
        web_url = Config.objects.get(key='web_url').value
        data['role_details'] = get_user_role_details(user)
        response_data = dict(user=data)
        data['is_follow'] = True if user_followed else False
        data['authentication_token'] = None
        data['share_url'] = '%s%s' % (web_url, str(vanity_url))
        data['celebrity'] = celebrity
        data['unseen_bookings'] = 0

        if user_logged_in and user_logged_in == user.id:
            (token, created) = Token.objects.get_or_create(user=user)
            data['authentication_token'] = token.key
            data['unseen_bookings'] = user.unseen_bookings if user_logged_in == user.id else 0
            (notifications, created) = SettingsNotifications.objects.get_or_create(user_id=user.id)
            data['notification_settings'] = NotificationSettingsSerializer(notifications).data
        else:
            data.pop('email', None)
        if data['celebrity']:
            celebrity_details = CelebrityManagement.retrieve_celebrity(self, user.id)
            if getattr(status, celebrity_details['status']) == 200:
                response_data['celebrity_details'] = celebrity_details['data']['celebrity']
            else:
                return self.jp_error_response('HTTP_400_BAD_REQUEST', celebrity_details['e_code'],
                                              celebrity_details['message'])
        return self.jp_response(s_code='HTTP_200_OK', data=response_data)

    def retrieve(self, request, pk):
        user_followed = True

        try:
            pk = self.verify_hash_token(pk)
            logged_in_user = None
            pk = int(pk)
        except Exception:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_SIGNUP', 'User Does not Exist')
        try:
            logged_in_user = StargramzUser.objects.values_list('id', flat=True).get(username=request.user)
        except StargramzUser.DoesNotExist:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_SIGNUP', 'User Does not Exist')

        try:
            CelebrityFollow.objects.get(fan_id=logged_in_user, celebrity_id=pk)
        except CelebrityFollow.DoesNotExist:
            user_followed = False

        if logged_in_user != pk:
            try:
                CelebrityView.objects.filter(fan_id=logged_in_user, celebrity_id=pk)
            except CelebrityView.DoesNotExist:
                CelebrityView.objects.create(fan_id=logged_in_user, celebrity_id=pk)

        return self.get_details(request, pk=pk, user_followed=user_followed, user_logged_in=logged_in_user)

    def update(self, request, pk):
        try:
            user = StargramzUser.objects.get(username=request.user)
        except StargramzUser.DoesNotExist:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_SIGNUP', 'Invalid Signup User')
        if user.id != int(pk):
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'UNKNOWN_QUERY', 'You cannot retrieve '
                                                                                   'this Stargram request')
        serializer = UsersProfileSerializer(data=request.data['user_details'], instance=user)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    user = serializer.save()
                    if user:
                        data = RegisterSerializer(user).data
                        (token, created) = Token.objects.get_or_create(user=pk)
                        data['authentication_token'] = token.key
                        (notifications, created) = SettingsNotifications.objects.get_or_create(user_id=user.id)
                        data['notification_settings'] = NotificationSettingsSerializer(notifications).data
                        response_data = {'user': data}

                        if check_celebrity_profile_exist(user):
                            celebrity_update = CelebrityManagement.\
                                update_celebrity(self, request.data['celebrity_details'], user.id)
                            if getattr(status, celebrity_update['status']) == 200:
                                response_data['celebrity_details'] = celebrity_update['data']['celebrity']
                            else:
                                raise ValidationError(code=celebrity_update['e_code'],
                                                      message=celebrity_update['message'])
                        return self.jp_response(s_code='HTTP_200_OK', data=response_data)
            except ValidationError as update_error:
                return self.jp_error_response('HTTP_400_BAD_REQUEST', update_error.code,
                                              update_error.message)
        else:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_CREATE',
                                          self.error_msg_string(serializer.errors))

    def verify_hash_token(self, pk):

        try:
            user_id = VanityUrl.objects.values_list('user', flat=True).get(name=pk)
            return int(user_id)
        except Exception:
            return pk



class DeviceToken(APIView, ResponseViewMixin):
    """
        Add/Update the device token
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)

    def post(self, request):
        user = StargramzUser.objects.get(username=request.user)
        serializer = DeviceTokenSerializer(data=request.data)

        if serializer.is_valid():
            DeviceTokens.objects.update_or_create(
                device_id=serializer.validated_data.get('device_id'),
                defaults={
                    'user': user,
                    'device_token': serializer.validated_data.get('device_token'),
                    'device_type': serializer.validated_data.get('device_type')
                }
            )

            return self.jp_response(s_code='HTTP_200_OK', data='Successfully added the device tokens.')
        else:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_CREATE',
                                          self.error_msg_string(serializer.errors))


class ContactSupport(APIView, ResponseViewMixin):
    """
        Sent email to support from the Fans request details screen
    """

    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)

    def post(self, request):
        serializer = ContactSupportSerializer(data=request.data)
        if serializer.is_valid():
            user = StargramzUser.objects.get(username=request.user)
            sender_email = SENDER_EMAIL
            support_email = SUPPORT_EMAIL

            subject = 'Starsona Contact Support'
            ctx = {
                'baseurl': BASE_URL,
                'username': user.first_name + ' ' + user.last_name,
                'email': user.username,
                'comments': serializer.validated_data.get('comments'),
            }
            html_template = get_template('../templates/emails/contact_support.html')
            html_content = html_template.render(ctx)
            mail_status = SendMail(subject, html_content, sender_email=sender_email, to=support_email)
            if mail_status:
                return self.jp_response(s_code='HTTP_200_OK', data='Submitted your comments to our support team')
        return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_LOGIN', self.error_msg_string(serializer.errors))


class RoleUpdate(APIView, ResponseViewMixin):
    """
        Change the user role(Switch the user to fan/celebrity)
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)

    def post(self, request):
        serializer = RoleUpdateSerializer(data=request.data)

        if serializer.is_valid():
            user = StargramzUser.objects.get(username=request.user)
            complete = True
            if serializer.validated_data.get('role') == ROLES.celebrity:
                complete = check_celebrity_profile_exist(user)

            user_role = Role.objects.get(code=serializer.validated_data.get('role'))
            roles_mapping = UserRoleMapping.objects.get(user=user)
            if roles_mapping.role.code == ROLES.celebrity and user_role.code == ROLES.fan and complete:
                try:
                    celebrity = Celebrity.objects.get(user=user)
                    if not celebrity.has_fan_account:
                        celebrity.has_fan_account = True
                        celebrity.save()
                except Exception:
                    pass
            roles_mapping.role = user_role
            roles_mapping.is_complete = True if user_role.code == ROLES.fan else complete
            roles_mapping.save()
            data = {}
            Token.objects.filter(user=user).delete()
            user = authenticate(username=user.username)
            (token, created) = Token.objects.get_or_create(user=user)  # token.key has the key
            user.authentication_token = token.key
            data['token'] = token.key
            update_last_login(None, user=user)

            return self.jp_response(s_code='HTTP_200_OK', data=data)
        else:
            return self.jp_error_response(
                'HTTP_400_BAD_REQUEST',
                'INVALID_LOGIN',
                self.error_msg_string(serializer.errors)
            )


class UpdateNotificationBadge(APIView, ResponseViewMixin):
    """
        Change the user role(Switch the user to fan/celebrity)
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)

    def get(self, request):
        user = StargramzUser.objects.get(username=request.user)
        user.notification_badge_count = 0
        user.save()
        return self.jp_response(s_code='HTTP_200_OK', data='Successfully updated notification badge count')


class AlertFan(APIView, ResponseViewMixin):
    """
        Alert Fan when celebrity is available
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)

    def post(self, request):
        fan = StargramzUser.objects.get(username=request.user)
        celebrity_id = request.data.get('celebrity', '')
        if celebrity_id and check_celebrity_profile_exist(celebrity_id):
            try:
                CelebrityAvailableAlert.objects.get(Q(fan_id=fan.id) &
                                                    Q(celebrity_id=celebrity_id) &
                                                    Q(notification_send=False))
            except CelebrityAvailableAlert.DoesNotExist:
                CelebrityAvailableAlert.objects.create(fan_id=fan.id, celebrity_id=celebrity_id)
            return self.jp_response(s_code='HTTP_200_OK', data='Notification would be send when celebrity is available')
        else:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_UPDATE', 'Invalid Celebrity User')


class ValidateSocialSignup(APIView, ResponseViewMixin):
    """
        Validate user is already register for social media logins
    """
    authentication_classes = ()
    permission_classes = (CustomPermission,)

    def post(self, request):
        serializer = ValidateSocialSignupSerializer(data=request.data)
        if serializer.is_valid():
            sign_up_source = serializer.validated_data.get('signup_source')
            social_id = serializer.validated_data.get('social_id')
            email = serializer.validated_data.get('email')
            try:
                if sign_up_source == SIGN_UP_SOURCE_CHOICES.facebook:
                    user = StargramzUser.objects.get(Q(fb_id=social_id) | Q(username=email))
                elif sign_up_source == SIGN_UP_SOURCE_CHOICES.instagram:
                    user = StargramzUser.objects.get(Q(in_id=social_id) | Q(username=email))
                elif sign_up_source == SIGN_UP_SOURCE_CHOICES.google:
                    user = StargramzUser.objects.get(Q(gp_id=social_id) | Q(username=email))

                return self.jp_response(s_code='HTTP_200_OK', data={'message': 'User is already registered'})
            except Exception:
                return self.jp_error_response(
                    'HTTP_400_BAD_REQUEST',
                    'INVALID_LOGIN',
                    'User doesnt exist'
                )
        else:
            return self.jp_error_response(
                'HTTP_400_BAD_REQUEST',
                'INVALID_LOGIN',
                self.error_msg_string(serializer.errors)
            )


class UpdateBookingCount(APIView, ResponseViewMixin):
    """
        Update the unseen count to 0
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)

    def get(self, request):
        try:
            user = StargramzUser.objects.get(username=request.user)
            user.unseen_bookings = 0
            user.save()
        except Exception:
            pass
        return self.jp_response(s_code='HTTP_200_OK', data='Successfully updated booking count')


class GetAWSSignedPostUrl(APIView, ResponseViewMixin):
    """
        Create post url for AWS file uploads
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)

    def get(self, request):
        serializer = AWSSignedURLSerializer(data=request.query_params)
        if serializer.is_valid():
            extension = serializer.validated_data.get('extension')
            file_type = serializer.validated_data.get('file_type')
            key = serializer.validated_data.get('key')
            constants_value = {
                'profile_images': PROFILE_IMAGES,
                'stargram_videos': STARGRAM_VIDEOS,
                'authentication_videos': AUTHENTICATION_VIDEOS
            }
            valid_extensions = {
                'image': ['png', 'jpg', 'jpeg'],
                'video': ['mp4'],
            }

            if extension and extension.lower() in valid_extensions[file_type]:
                file_name = '%sFILE_%s%s.%s' % (constants_value[key], int(time.time()), generate_random_code(8), str(extension))
                url = get_pre_signed_post_url(file_name, 60, 120, True)
                return self.jp_response(s_code='HTTP_200_OK', data=url)
            else:
                return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_LOGIN', 'Invalid extension')
        else:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_LOGIN', serializer.errors)


class GetAWSSignedUrl(APIView, ResponseViewMixin):
    """
        Create post url for AWS file uploads
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)

    def get(self, request):
        serializer = AWSPreSignedURLSerializer(data=request.query_params)
        if serializer.is_valid():
            file_name = serializer.validated_data.get('file_name')
            key = serializer.validated_data.get('key')
            constants_value = {
                'profile_images': PROFILE_IMAGES,
                'stargram_videos': STARGRAM_VIDEOS,
                'authentication_videos': AUTHENTICATION_VIDEOS
            }

            if key in constants_value:
                url = get_pre_signed_get_url(file_name, constants_value[key])
                return self.jp_response(s_code='HTTP_200_OK', data=url)
            else:
                return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_LOGIN', 'Invalid extension')
        else:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_LOGIN', serializer.errors)