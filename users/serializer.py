import django.contrib.auth.password_validation as validators
from django.contrib.auth.models import update_last_login
from django.contrib.auth import authenticate
from django.core import exceptions, validators as SerialValidator
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from rest_framework.authtoken.models import Token
from utilities.konstants import INPUT_DATE_FORMAT, OUTPUT_DATE_FORMAT, ROLES
from config.models import Config
from config.constants import *
from .models import StargramzUser, SIGN_UP_SOURCE_CHOICES, Celebrity, Profession, UserRoleMapping, ProfileImage, \
    CelebrityAbuse, CelebrityProfession, CelebrityFollow, DeviceTokens, SettingsNotifications, FanRating, Referral,\
    VanityUrl, GroupAccount, GroupType, CelebrityGroupAccount, SocialMediaLinks, Representative, AdminReferral
from .impersonators import IMPERSONATOR
from role.models import Role
from datetime import datetime, timedelta
from django.utils import timezone
from .constants import LINK_EXPIRY_DAY, ROLE_ERROR_CODE, EMAIL_ERROR_CODE, NEW_OLD_SAME_ERROR_CODE, \
    OLD_PASSWORD_ERROR_CODE, PROFILE_PHOTO_REMOVED, MAX_RATING_VALUE, MIN_RATING_VALUE, FIRST_NAME_ERROR_CODE
from utilities.utils import CustomModelSerializer, get_pre_signed_get_url, datetime_range, get_s3_public_url,\
    get_user_id, get_bucket_url, encode_pk
import re
from utilities.permissions import CustomValidationError, error_function
from rest_framework import status
from stargramz.models import Stargramrequest, STATUS_TYPES
from django.db.models import Q, Sum
from utilities.constants import BASE_URL
from .tasks import welcome_email, representative_email
from job.tasks import send_message_to_slack
from payments.models import PaymentPayout
from hashids import Hashids
import pytz
hashids = Hashids(min_length=8)


class ProfilePictureSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField(read_only=True)
    photo = serializers.CharField(read_only=True)
    thumbnail = serializers.CharField(read_only=True)
    image_url = serializers.SerializerMethodField('get_s3_image_url')
    thumbnail_url = serializers.SerializerMethodField('get_s3_thumbnail_url')
    medium_thumbnail = serializers.CharField(read_only=True)
    medium_thumbnail_url = serializers.SerializerMethodField('get_s3_medium_thumbnail_url')

    def __init__(self, *args, **kwargs):
        self.bucket_url = get_bucket_url()
        super().__init__(*args, **kwargs)

    class Meta:
        model = ProfileImage
        fields = ('id', 'image_url', 'thumbnail_url', 'photo', 'thumbnail', 'medium_thumbnail', 'medium_thumbnail_url')

    def get_s3_image_url(self, obj):
        config = PROFILE_IMAGES
        return '{}/{}'.format(self.bucket_url, config+obj.photo)

    def get_s3_thumbnail_url(self, obj):
        if obj.thumbnail is not None:
            config = PROFILE_IMAGES
            return '{}/{}'.format(self.bucket_url, config+obj.thumbnail)
        else:
            return None

    def get_s3_medium_thumbnail_url(self, obj):
        if obj.medium_thumbnail is not None:
            config = PROFILE_IMAGES
            return '{}/{}'.format(self.bucket_url, config+obj.medium_thumbnail)
        else:
            return None

    def get_id(self, obj):
        return encode_pk(obj.id)


class RoleDetailSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=True)
    role_code = serializers.CharField(required=True)
    role_name = serializers.CharField(required=True)
    is_complete = serializers.BooleanField(required=True)

    class Meta:
        model = UserRoleMapping


class RegisterSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField(read_only=True)
    email = serializers.EmailField(required=True, allow_blank=False)
    password = serializers.CharField(required=True, allow_blank=False, write_only=True)
    authentication_token = serializers.CharField(read_only=True)
    first_name = serializers.CharField(required=True, allow_blank=False)
    last_name = serializers.CharField(required=False, allow_blank=True)
    date_of_birth = serializers.DateField(input_formats=INPUT_DATE_FORMAT, format=OUTPUT_DATE_FORMAT, required=False)
    role_details = RoleDetailSerializer(read_only=True)
    images = serializers.SerializerMethodField(read_only=True)
    role = serializers.ChoiceField(choices=ROLES.choices(), write_only=True)
    avatar_photo = ProfilePictureSerializer(read_only=True)
    featured_photo = ProfilePictureSerializer(read_only=True)
    show_nick_name = serializers.BooleanField(read_only=True)
    completed_fan_unseen_count = serializers.IntegerField(read_only=True, source="completed_view_count")
    referral_code = serializers.CharField(required=False, allow_blank=True, write_only=True)
    promo_code = serializers.SerializerMethodField(read_only=True)
    user_id = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = StargramzUser
        fields = ('first_name', 'last_name', 'nick_name', 'id', 'email', 'password', 'date_of_birth', 'featured_photo',
                  'authentication_token', 'status', 'sign_up_source', 'role_details', 'images', 'profile_photo',
                  'role', 'avatar_photo', 'show_nick_name', 'completed_fan_unseen_count', 'referral_code', 'promo_code',
                  'user_id', 'has_requested_referral', 'stripe_user_id', 'check_payments')
        depth = 1

    def validate_email(self, value):
        email = value.lower()
        user = StargramzUser.objects.filter(email=email)
        if user:
            user = user[0]
            if user.expiry_date and user.expiry_date < datetime.now(pytz.timezone('UTC')):
                user.delete()
                return email
            elif not user.is_active:
                raise serializers.ValidationError(
                    'The email has already been registered and deactivated. Please contact Starsona Admin'
                )
            else:
                raise serializers.ValidationError("The email has already been registered.")
        else:
            return email

    def validate(self, data):
        errors = dict()
        dob = data.get('date_of_birth', '')
        if dob:
            if user_dob_validate(data):
                errors['date_of_birth'] = 'Age should be above 17.'
        try:
            validators.validate_password(password=data['password'])
        except exceptions.ValidationError as e:
            errors['password'] = list(e.messages)

        if errors:
            raise serializers.ValidationError(errors)

        return data

    def get_promo_code(self, obj):
        return obj.referral_code if obj.referral_active and obj.referral_campaign else None

    def get_user_id(self, obj):
        try:
            return VanityUrl.objects.values_list('name', flat=True).get(user=obj.id)
        except Exception:
            return ''

    def get_id(self, obj):
        return encode_pk(obj.id)

    def get_images(self, obj):
        exclude_ids = []
        if obj.avatar_photo_id:
            exclude_ids.append(obj.avatar_photo_id)
        if obj.featured_photo_id:
            exclude_ids.append(obj.featured_photo_id)
        query = ProfileImage.objects.filter(user=obj.id).order_by('-created_date').exclude(id__in=exclude_ids)
        serializer = ProfilePictureSerializer(query, many=True)
        return serializer.data

    def create(self, validated_data):
        email = validated_data.get('email')
        password = validated_data.get('password')
        first_name = validated_data.get('first_name')
        last_name = validated_data.get('last_name')
        nick_name = validated_data.get('nick_name')
        dob = validated_data.get('date_of_birth', '')
        roles = validated_data.get('role', '')
        referral_code = validated_data.get('referral_code', '')

        try:
            user = StargramzUser.objects.create(username=email, email=email, nick_name=nick_name,
                                                first_name=first_name, last_name=last_name)

            try:
                referral = AdminReferral.objects.get(referral_code=referral_code, activate=True)
                user.admin_approval_referral_code = referral
                user.save()
            except Exception:
                pass
            user.show_nick_name = True if nick_name else False
            if dob:
                user.date_of_birth = dob
            user.set_password(password)
            user.save()

            role = Role.objects.get(code=ROLES.fan)
            if roles:
                role = Role.objects.get(code=roles)

            is_complete = False
            if roles == ROLES.fan:
                is_complete = True

            user_role, created = UserRoleMapping.objects.get_or_create(
                user=user,
                role=role,
                is_complete=is_complete
            )
            if is_complete:
                welcome_email.delay(user.pk)
                # when a fan created, a message will send to the slack
                slack_template = "new_user_fan"
                slack_ctx = {
                    "fan_name": user.get_short_name()
                }
                send_message_to_slack.delay(slack_template, slack_ctx)

            old_user_roles = UserRoleMapping.objects.filter(user=user).exclude(id=user_role.id)
            old_user_roles.delete()

            # Referral Program
            create_referral(referral_code=referral_code, user=user)

            user = authenticate(username=email, password=password)
            (token, created) = Token.objects.get_or_create(user=user)  # token.key has the key
            user.authentication_token = token.key
            update_last_login(None, user=user)
            return user
        except Exception as e:
            try:
                user.delete()
            except Exception:
                pass
            raise serializers.ValidationError(str(e))


def create_referral(referral_code, user):
    """
        Links the referrer and referee
    """
    if referral_code:
        try:
            referrer_id = StargramzUser.objects.values_list('id', flat=True) \
                .get(referral_code=referral_code.upper(), referral_active=True)
            Referral.objects.create(referrer_id=referrer_id, referee=user, source="branch.io")
            referrer = StargramzUser.objects.get(id=referrer_id)
            if referrer.is_ambassador:
                user.ambassador = referrer
                user.save()
        except StargramzUser.DoesNotExist:
            pass
    return True


class LoginSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField(read_only=True)
    username = serializers.CharField(required=True, allow_blank=False, write_only=True)
    password = serializers.CharField(required=True, allow_blank=False, write_only=True)
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)
    authentication_token = serializers.CharField(read_only=True)
    images = ProfilePictureSerializer(many=True, read_only=True)
    avatar_photo = ProfilePictureSerializer(read_only=True)
    show_nick_name = serializers.BooleanField(read_only=True)
    completed_fan_unseen_count = serializers.IntegerField(read_only=True, source="completed_view_count")

    class Meta:
        model = StargramzUser
        fields = ('first_name', 'last_name', 'nick_name', 'id', 'username', 'email', 'password', 'authentication_token',
                  'status', 'sign_up_source', 'images', 'profile_photo', 'avatar_photo', 'show_nick_name',
                  'completed_fan_unseen_count')

    def validate_username(self, value):
        return value.lower()

    def get_id(self, obj):
        return encode_pk(obj.id)

    def validate(self, data):
        user = authenticate(username=data.get('username'), password=data['password'])
        if user is not None:
            # the password verified for the user
            try:
                role_code = UserRoleMapping.objects.get(user=user).role.code
            except:
                role_code = None
            if self.context.get('booking_condition', None) and role_code and role_code == ROLES.celebrity:
                raise serializers.ValidationError('Booking a video is only available for Starsona fan accounts.')
            if user.is_active:
                (token, created) = Token.objects.get_or_create(user=user)  # token.key has the key
                user.authentication_token = token.key
                user.sign_up_source = SIGN_UP_SOURCE_CHOICES.regular
                user.save()
                update_last_login(None, user=user)
                return user
            else:
                raise serializers.ValidationError('Your account has been deactivated. Please contact Starsona Admin')
        else:
            raise serializers.ValidationError({"error": "The username/password is incorrect."})


class EmailSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)

    class Meta:
        model = StargramzUser
        fields = ['email']

    def validate_email(self, value):
        email = value.lower()
        if StargramzUser.objects.filter(email=email).exists():
            raise serializers.ValidationError("The email has already been registered.")
        return email


class SocialSignupSerializer(serializers.ModelSerializer):
    username = serializers.CharField(required=True)
    authentication_token = serializers.CharField(read_only=True)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    sign_up_source = serializers.IntegerField(required=True)
    role_details = RoleDetailSerializer(read_only=True)
    role = serializers.ChoiceField(choices=ROLES.choices(), required=False, write_only=True)
    avatar_photo = ProfilePictureSerializer(read_only=True)
    show_nick_name = serializers.BooleanField(read_only=True)
    completed_fan_unseen_count = serializers.IntegerField(read_only=True, source="completed_view_count")

    class Meta:
        model = StargramzUser
        fields = ('first_name', 'last_name', 'id', 'email', 'username', 'date_of_birth', 'authentication_token',
                  'sign_up_source', 'role_details', 'profile_photo', 'nick_name', 'fb_id', 'gp_id', 'in_id', 'tw_id',
                  'role', 'avatar_photo', 'show_nick_name', 'completed_fan_unseen_count', 'referral_code')

    def validate_username(self, value):
        return value.lower()

    def validate(self, data):
        errors = dict()
        sign_up_source = data.get('sign_up_source', '')
        signup_choices = [i[0] for i in SIGN_UP_SOURCE_CHOICES.choices()]
        if int(sign_up_source) not in signup_choices and int(sign_up_source) > 1:
            raise serializers.ValidationError('Please provide a valid Sign up Source')

        if errors:
            raise serializers.ValidationError(errors)

        return data

    def create(self, validated_data):
        dob = validated_data.get('date_of_birth', '')
        email = validated_data.get('username')
        first_name = validated_data.get('first_name', '')
        last_name = validated_data.get('last_name', '')
        sign_up_source = validated_data.get('sign_up_source')
        profile_photo = validated_data.get('profile_photo')
        nick_name = validated_data.get('nick_name', None)
        fb_id = validated_data.get('fb_id')
        gp_id = validated_data.get('gp_id')
        in_id = validated_data.get('in_id')
        tw_id = validated_data.get('tw_id')
        roles = validated_data.get('role', '')
        referral_code = validated_data.get('referral_code', '')
        try:
            if sign_up_source == SIGN_UP_SOURCE_CHOICES.facebook and fb_id:
                user = StargramzUser.objects.get(Q(fb_id=fb_id) | Q(username=email))
                user.fb_id = fb_id
            elif sign_up_source == SIGN_UP_SOURCE_CHOICES.instagram and in_id:
                user = StargramzUser.objects.get(Q(in_id=in_id) | Q(username=email))
                user.in_id = in_id
            elif sign_up_source == SIGN_UP_SOURCE_CHOICES.google and gp_id:
                user = StargramzUser.objects.get(Q(gp_id=gp_id) | Q(username=email))
                user.gp_id = gp_id
            elif sign_up_source == SIGN_UP_SOURCE_CHOICES.twitter and tw_id:
                user = StargramzUser.objects.get(Q(tw_id=tw_id) | Q(username=email))
                user.tw_id = tw_id
            else:
                user = StargramzUser.objects.get(username=email)
            if user.profile_photo != PROFILE_PHOTO_REMOVED:
                user.profile_photo = profile_photo
            user.sign_up_source = sign_up_source
            if nick_name:
                user.nick_name = nick_name
                user.show_nick_name = True
            user.save()
            try:
                role_code = UserRoleMapping.objects.get(user=user).role.code
            except:
                role_code = None
            if self.context.get('booking_condition', None) and role_code and role_code == ROLES.celebrity:
                return {'code': 'booking', 'message': 'Booking a video is only available for Starsona fan accounts.'}
        except StargramzUser.DoesNotExist:
            try:
                if not roles:
                    return {'code': ROLE_ERROR_CODE, 'message': 'Please enter role'}
                if not re.match("(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)", email):
                    return {'code': EMAIL_ERROR_CODE, 'message': 'Please enter a valid email'}
                if not first_name:
                    return {'code': FIRST_NAME_ERROR_CODE, 'message': 'Please enter first name'}

                user = StargramzUser.objects.create(username=email, email=email, first_name=first_name,
                                                    last_name=last_name, sign_up_source=sign_up_source,
                                                    profile_photo=profile_photo, nick_name=nick_name,
                                                    fb_id=fb_id, gp_id=gp_id, in_id=in_id, tw_id=tw_id)

                try:
                    referral = AdminReferral.objects.get(referral_code=referral_code, activate=True)
                    user.admin_approval_referral_code = referral
                    user.save()
                except Exception:
                    pass

                if dob:
                    user.date_of_birth = dob
                user.show_nick_name = True if nick_name else False
                user.set_unusable_password()
                user.save()
                is_complete = False
                role = Role.objects.get(code=ROLES.fan)
                if roles:
                    role = Role.objects.get(code=roles)
                if role.code == ROLES.fan:
                    is_complete = True

                create_referral(referral_code=referral_code, user=user)
                user_role, created = UserRoleMapping.objects.get_or_create(user=user, role=role,
                                                                           is_complete=is_complete)
                if is_complete:
                    welcome_email.delay(user.pk)
                old_user_roles = UserRoleMapping.objects.filter(user=user).exclude(id=user_role.id)
                old_user_roles.delete()
            except Exception as e:
                try:
                    user.delete()
                except Exception:
                    pass
                raise serializers.ValidationError(str(e))
        user = authenticate(username=user.username)
        (token, created) = Token.objects.get_or_create(user=user)  # token.key has the key
        user.authentication_token = token.key
        update_last_login(None, user=user)
        return user


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True, allow_blank=False)

    def validate(self, data):
        user = StargramzUser.objects.filter(email=data.get('email'))
        if user and user[0].expiry_date:
            raise serializers.ValidationError('Account with this email is not completed')
        return data



class ResetPasswordSerializer(serializers.Serializer):
    reset_id = serializers.UUIDField(required=True, allow_null=False)
    password = serializers.CharField(required=True, allow_blank=False)

    def validate(self, data):
        errors = dict()
        reset_id = data.get('reset_id', '')
        password = data.get('password', '')
        try:
            user = StargramzUser.objects.get(reset_id=reset_id)
        except StargramzUser.DoesNotExist:
            raise serializers.ValidationError('The Link doesnot exist anymore')
        if user.expiry_date:
            raise serializers.ValidationError('Account with this email is not completed')
        if not user.is_active:
            raise serializers.ValidationError('Your account has been deactivated. Please contact Starsona Admin')
        if (timezone.now() - user.reset_generate_time) > timedelta(LINK_EXPIRY_DAY):
            raise serializers.ValidationError('The Link has been expired')
        try:
            validators.validate_password(password=password)
        except exceptions.ValidationError as e:
            errors['password'] = list(e.messages)

        if errors:
            raise serializers.ValidationError(errors)

        return data


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, allow_blank=False, allow_null=False)
    new_password = serializers.CharField(required=True, allow_blank=False, allow_null=False)

    def validate(self, data):
        old_password = data.get('old_password', '')
        new_password = data.get('new_password', '')
        user = self.context.get('user')
        if not user.check_password(old_password):
            raise CustomValidationError(detail=error_function(OLD_PASSWORD_ERROR_CODE,
                                                              'Old Password does not match'),
                                        status_code=status.HTTP_200_OK)
        if user.check_password(new_password):
            raise CustomValidationError(detail=error_function(NEW_OLD_SAME_ERROR_CODE,
                                                              'New and Old Password cannot be same'),
                                        status_code=status.HTTP_200_OK)
        try:
            validators.validate_password(new_password)
        except Exception as e:
            raise serializers.ValidationError(str(e))
        return data


class ProfessionChildSerializer(serializers.RelatedField):
    def to_representation(self, value):
        serializer = self.parent.parent.__class__(value, context=self.context)
        return serializer.data


class ProfessionSerializer(serializers.ModelSerializer):
    child = serializers.SerializerMethodField()
    file = serializers.SerializerMethodField()

    def get_file(self, obj):
        return None

    def get_child(self, obj):
        return ChildSerializer(Profession.objects.filter(parent=obj.id), many=True).data

    class Meta:
        model = Profession
        fields = ('id', 'title', 'parent', 'child', 'file', 'order')


class ChildSerializer(serializers.ModelSerializer):
    file = serializers.SerializerMethodField()
    child = serializers.SerializerMethodField()

    def get_file(self, obj):
        return None

    def get_child(self, obj):
        return []

    class Meta:
        model = Profession
        fields = ('id', 'title', 'parent', 'child', 'file', 'order')

class ProfessionFilterSerializer(serializers.ModelSerializer):
    file = serializers.SerializerMethodField()
    child = serializers.SerializerMethodField()

    def get_child(self, obj):
        query_set = CelebrityProfession.objects \
            .filter(profession__parent=obj.id) \
            .values_list('profession', flat=True).distinct()
        profession = Profession.objects.filter(id__in=query_set)

        return ChildSerializer(profession, many=True).data

    def get_file(self, obj):
        return None

    class Meta:
        model = Profession
        fields = ('id', 'title', 'parent', 'child', 'file', 'order')


class CelebrityProfileSerializer(CustomModelSerializer):
    # rate = serializers.SerializerMethodField()
    profession_name = serializers.CharField(read_only=True, source="profession.title")
    profession = serializers.ListField(required=False, allow_empty=False, max_length=3)
    availability = serializers.BooleanField(required=True)
    pending_requests_count = serializers.SerializerMethodField(read_only=True)

    # def get_rate(self, obj):
    #     return str(int(obj.rate))

    class Meta:
        model = Celebrity
        extra_kwargs = {"rate": {"error_messages": {"max_digits": "The booking price is too high"}}}
        fields = '__all__'

    def get_pending_requests_count(self, obj):
        pending_count = Stargramrequest.objects.filter(Q(celebrity_id=obj.user_id) &
                                                       Q(request_status=STATUS_TYPES.pending)).count()
        return pending_count

    def validate(self, data):
        professions = data.get('profession')
        if not self.instance:
            if not professions:
                raise serializers.ValidationError("Profession is required")
            profession_list = Profession.objects.values_list('id', flat=True)
            for profession in professions:
                if int(profession) not in profession_list:
                    raise serializers.ValidationError("Profession Not in available Choices")
        return data

    def create(self, validated_data):
        user_id = validated_data.get('user')
        rate = validated_data.get('rate')
        in_app_price = validated_data.get('in_app_price')
        weekly_limits = validated_data.get('weekly_limits')
        profile_video = validated_data.get('profile_video')
        duration = validated_data.get('duration')
        professions = validated_data.get('profession')
        availability = validated_data.get('availability')
        description = validated_data.get('description', '')
        charity = validated_data.get('charity', '')
        celebrity = Celebrity.objects.\
            create(rate=rate, in_app_price=in_app_price, weekly_limits=weekly_limits, profile_video=profile_video,
                   user=user_id, availability=availability, description=description, charity=charity, duration=duration)
        for profession in professions:
            CelebrityProfession.objects.create(user=user_id, profession_id=profession)

        # when a celebrity created a message will send to the slack
        try:
            user = StargramzUser.objects.get(username=user_id)
            web_url = Config.objects.get(key="web_url").value
            slack_template = "new_user_celebrity"
            slack_ctx = {
                "celebrity_name": user.get_short_name(),
                "celebrity_link": "%s%s" % (web_url, user.vanity_urls.name)
            }
            send_message_to_slack.delay(slack_template, slack_ctx)
        except Exception as e:
            print(str(e))
        return celebrity

    def update(self, instance, validated_data):
        if validated_data.get('profession'):
            professions = validated_data.get('profession')
            CelebrityProfession.objects.filter(user=instance.user_id).delete()
            for profession in professions:
                CelebrityProfession.objects.create(user_id=instance.user_id, profession_id=profession)
        field_list = ['rate', 'in_app_price', 'weekly_limits', 'availability', 'description', 'charity',
                      'profile_video', 'duration', 'website']
        for list_item in field_list:
            if list_item in validated_data:
                setattr(instance, list_item, validated_data.get(list_item))
        instance.save()

        return instance


class CelebrityProfessionSerializer(serializers.ModelSerializer):

    def __init__(self, *args, **kwargs):
        mains = {}
        try:
            professions = Profession.objects.filter(parent=None).values('title', 'id')
            for profession in professions:
                mains.update({profession['id']: profession['title']})
        except Exception:
            pass
        self.parent_professions = mains
        super().__init__(*args, **kwargs)

    title = serializers.CharField(read_only=True, source="profession.title")
    id = serializers.IntegerField(read_only=True, source="profession.id")
    show_parent = serializers.SerializerMethodField(read_only=True)
    parent = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CelebrityProfession
        fields = ['id', 'title', 'show_parent', 'parent']


    def get_show_parent(self, obj):
        # Only Impersonators profession to display in front end
        if obj.profession.id in IMPERSONATOR:
            return True
        return False

    def get_parent(self, obj):
        try:
            return self.parent_professions.get(obj.profession.parent_id)
        except Exception:
            return None


class ProfessionTitleSerializer(serializers.ModelSerializer):
    title = serializers.CharField(read_only=True, source="profession.title")

    class Meta:
        model = CelebrityProfession
        fields = ['title']


class ProfileImageListSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(required=False)
    photo = serializers.CharField(required=True)


class ProfileImageSerializer(serializers.Serializer):
    images_list = ProfileImageListSerializer(many=True)
    avatar_photo = serializers.CharField(required=False, write_only=True, allow_blank=True)

    def validate(self, data):
        avatar_photo = data.get('avatar_photo', '')
        request_images = self.context['request'].data['images']
        if avatar_photo:
            if avatar_photo not in request_images:
                raise serializers.ValidationError("Avatar image must be of the above images list")
        return data

    def create(self, validated_data):
        images_list = validated_data.get('images_list')
        request = self.context.get('request')
        request.data['user'].avatar_photo_id = None
        request.data['user'].save()
        images = ProfileImage.objects.filter(user=request.data['user'])
        if images.exists():
            images.delete()
        profile_images = [ProfileImage(user=request.data['user'], photo=item['photo']) for item in images_list]

        return ProfileImage.objects.bulk_create(profile_images)


class ImageRemoveSerializer(serializers.Serializer):
    id = serializers.ListField(required=True)


class UsersProfileSerializer(serializers.ModelSerializer):
    date_of_birth = serializers.DateField(input_formats=INPUT_DATE_FORMAT, format=OUTPUT_DATE_FORMAT, required=False)
    first_name = serializers.CharField(max_length=128, allow_blank=True, required=False)

    class Meta:
        model = StargramzUser
        fields = ('first_name', 'last_name', 'date_of_birth', 'nick_name', 'profile_photo', 'show_nick_name',
                  'check_payments')

    def validate(self, data):
        errors = dict()
        dob = data.get('date_of_birth', '')
        if dob:
            if user_dob_validate(data):
                errors['date_of_birth'] = 'Age should be above 17.'
        if errors:
            raise serializers.ValidationError(errors)

        return data

    def update(self, instance, validated_data):
        field_list = ['first_name', 'last_name', 'date_of_birth', 'nick_name', 'profile_photo', 'show_nick_name',
                      'check_payments']
        for list_item in field_list:
            if list_item in validated_data:
                setattr(instance, list_item, validated_data.get(list_item))
        instance.save()

        return instance


def user_dob_validate(data):
    dob = data['date_of_birth'].strftime('%d/%m/%Y')
    date1 = datetime.strptime(dob, "%d/%m/%Y")
    date2 = datetime.strptime(datetime.now().strftime("%d/%m/%Y"), "%d/%m/%Y")
    diff = date2 - date1
    (age, days) = divmod(diff.days, 365)
    if age < 13:
        return True
    return False


class CelebritySerializer(serializers.RelatedField):

    def get_attribute(self, instance):
        try:
            return instance.celebrity_user
        except Exception:
            celebrity = Celebrity()
            celebrity.rate = 0.00
            celebrity.rating = 0.00
            celebrity.weekly_limits = 0
            celebrity.follow_count = 0
            celebrity.charity = ""
            return celebrity

    def to_representation(self, value):
        if not value.in_app_price:
            in_app_price = value.rate
        elif value.rate > 1000:
            in_app_price = value.rate
        else:
            in_app_price = value.in_app_price

        return {'rate': str(int(value.rate)), 'in_app_price': str(float(in_app_price)), 'rating': str(value.rating),
                'weekily_limits': value.weekly_limits, 'follow_count': value.follow_count,
                'charity': value.charity}


class HasGroupAccountSerializer(serializers.BooleanField):

    def get_attribute(self, instance):
        try:
            if instance.group_account:
                return True
            else:
                return False
        except Exception:
            return False


class UserSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField(read_only=True)
    celebrity_user = CelebritySerializer(read_only=True)
    celebrity_follow = serializers.SerializerMethodField(read_only=True, required=False)
    celebrity_profession = CelebrityProfessionSerializer(read_only=True, many=True)
    avatar_photo = ProfilePictureSerializer(read_only=True)
    featured_photo = ProfilePictureSerializer(read_only=True)
    images = serializers.SerializerMethodField()
    show_nick_name = serializers.BooleanField(read_only=True)
    user_id = serializers.CharField(read_only=True, source="vanity_urls.name")
    has_group_account = HasGroupAccountSerializer(read_only=True)
    group_type = serializers.CharField(read_only=True, source="group_account.group_type")

    def get_images(self, obj):
        if not obj.avatar_photo_id:
            query = ProfileImage.objects.filter(user=obj.id).order_by('-created_date')[:1]
            serializer = ProfilePictureSerializer(query, many=True)
            return serializer.data
        else:
            return [{}]

    def get_celebrity_follow(self, obj):
        if self.context['request'].user:
            user = StargramzUser.objects.get(username=self.context['request'].user)
            try:
                CelebrityFollow.objects.get(fan=user, celebrity_id=obj.id)
                return True
            except CelebrityFollow.DoesNotExist:
                return False
        return None

    def get_id(self, obj):
        return encode_pk(obj.id)

    class Meta:
        model = StargramzUser
        fields = ('id', 'first_name', 'last_name', 'nick_name', 'celebrity_user', 'images', 'celebrity_profession',
                  'celebrity_follow', 'avatar_photo', 'show_nick_name', 'get_short_name', 'featured_photo', 'user_id',
                  'group_type', 'has_group_account')


class CelebrityRatingSerializerEncoder(serializers.ModelSerializer):
    celebrity = serializers.SerializerMethodField(read_only=True)
    fan = serializers.SerializerMethodField(read_only=True)
    starsona = serializers.SerializerMethodField(read_only=True)
    comments = serializers.CharField(max_length=260, allow_blank=True, required=False)
    overall_rating = serializers.DecimalField(read_only=True, max_digits=6, decimal_places=2,
                                              source="celebrity.celebrity_user.rating")

    class Meta:
        model = FanRating
        fields = ('fan', 'celebrity', 'comments', 'reason', 'overall_rating', 'fan_rate', 'starsona')

    def get_celebrity(self, obj):
        return encode_pk(obj.celebrity.id)

    def get_fan(self, obj):
        return encode_pk(obj.fan.id)

    def get_starsona(self, obj):
        return encode_pk(obj.starsona.id)


class CelebrityRatingSerializer(serializers.ModelSerializer):
    comments = serializers.CharField(max_length=260, allow_blank=True, required=False)
    overall_rating = serializers.DecimalField(read_only=True, max_digits=6, decimal_places=2,
                                              source="celebrity.celebrity_user.rating")

    class Meta:
        model = FanRating
        fields = ('fan', 'celebrity', 'comments', 'reason', 'overall_rating', 'fan_rate', 'starsona')

    def validate(self, data):
        celebrity = data.get('celebrity')
        fan = data.get('fan')
        starsona = data.get('starsona')
        try:
            Stargramrequest.objects.get(fan=fan, celebrity=celebrity, id=starsona.id)
            return data
        except Stargramrequest.DoesNotExist:
            raise serializers.ValidationError('Booking does not exist for this user')


class CelebrityFollowSerializer(serializers.Serializer):
    follow = serializers.BooleanField(required=True)
    celebrity = serializers.IntegerField(required=True)


class CelebrityAbuseSerializer(serializers.ModelSerializer):

    class Meta:
        model = CelebrityAbuse
        fields = ('celebrity', 'abuse_comment', 'fan')


class SuggestionSerializer(serializers.ModelSerializer):
    celebrity_profession = ProfessionTitleSerializer(read_only=True, many=True)
    avatar_photo = ProfilePictureSerializer(read_only=True)
    user_id = serializers.CharField(read_only=True, source="vanity_urls.name")
    has_group_account = HasGroupAccountSerializer(read_only=True)
    group_type = serializers.CharField(read_only=True, source="group_account.group_type")
    id = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = StargramzUser
        fields = ('id', 'first_name', 'last_name', 'nick_name', 'get_short_name', 'celebrity_profession',
                  'avatar_photo', 'user_id', 'has_group_account', 'group_type')

    def get_id(self, obj):
        return encode_pk(obj.id)


class DeviceTokenSerializer(serializers.ModelSerializer):

    class Meta:
        model = DeviceTokens
        fields = ('device_type', 'device_id', 'device_token')


class NotificationSettingsSerializerEncode(CustomModelSerializer):
    user = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = SettingsNotifications
        fields = '__all__'

    def get_user(self, obj):
        return encode_pk(obj.user.id)


class NotificationSettingsSerializer(CustomModelSerializer):
    id = serializers.IntegerField(write_only=True)
    secondary_email = serializers.EmailField(required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = SettingsNotifications
        fields = '__all__'

    def validate_secondary_email(self, value):
        email = value.lower()
        if StargramzUser.objects.filter(email=email).exists():
            raise serializers.ValidationError("The email has already been registered.")
        return email


class ContactSupportSerializer(serializers.Serializer):
    """
        Comments field serializer
    """

    comments = serializers.CharField(required=True)


class RoleUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(required=True, choices=ROLES.choices(), write_only=True)

    class Meta:
        model = UserRoleMapping
        fields = ('role', 'role_details')


class ReferralUserSerializer(serializers.ModelSerializer):
    celebrity_profession = CelebrityProfessionSerializer(read_only=True, many=True)
    avatar_photo = ProfilePictureSerializer(read_only=True)
    show_nick_name = serializers.BooleanField(read_only=True)
    referral_amounts = serializers.SerializerMethodField(read_only=True, required=False)

    def get_referral_amounts(self, obj):
        users_amount = PaymentPayout.objects.filter(transaction__celebrity_id=obj.id, referral_payout=True)\
            .aggregate(payed_out=Sum('fund_payed_out'))

        return float(0 if not users_amount.get('payed_out', None) else users_amount.get('payed_out')).__format__('.2f')

    class Meta:
        model = StargramzUser
        fields = ('id', 'first_name', 'last_name', 'nick_name', 'celebrity_profession',
                  'avatar_photo', 'show_nick_name', 'referral_amounts')


class ValidateSocialSignupSerializer(serializers.Serializer):
    signup_source = serializers.ChoiceField(choices=SIGN_UP_SOURCE_CHOICES.choices(), required=True, write_only=True)
    social_id = serializers.CharField(required=True, write_only=True)
    email = serializers.EmailField(required=False, write_only=True, allow_blank=True)

    class Meta:
        fields = ('sign_up_source', 'social_id', 'email')


class AWSSignedURLSerializer(serializers.Serializer):
    key = serializers.ChoiceField(
        required=True,
        write_only=True,
        choices=['profile_images', 'stargram_videos', 'authentication_videos', 'reactions']
    )
    extension = serializers.ChoiceField(
        required=True,
        write_only=True,
        choices=['png', 'jpg', 'jpeg', 'mp4']
    )
    file_type = serializers.ChoiceField(choices=['image', 'video'], required=True, write_only=True)

    class Meta:
        fields = ('key', 'file_type', 'extension')


class AWSPreSignedURLSerializer(serializers.Serializer):
    key = serializers.ChoiceField(
        required=True,
        write_only=True,
        choices=['profile_images', 'stargram_videos', 'authentication_videos']
    )
    file_name = serializers.CharField(required=True, write_only=True)

    class Meta:
        fields = ('key', 'file_name')


class GroupAccountSerializer(CustomModelSerializer):

    grouptype = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = GroupAccount
        fields = '__all__'

    def create(self, validated_data):
        user_id = validated_data.get('user')
        group_account, created_date = GroupAccount.objects.update_or_create(user=user_id, defaults=validated_data)
        roles_mapping = UserRoleMapping.objects.get(user=user_id)
        roles_mapping.is_complete = True
        roles_mapping.save()
        welcome_email.delay(group_account.user_id)
        group_account.admin_approval = True
        group_account.save()
        return group_account

    def update(self, instance, validated_data):
        field_list = ['contact_first_name', 'contact_last_name', 'group_type', 'description', 'tags', 'website',
                      'phone', 'address', 'address_2', 'city', 'state', 'zip', 'country']
        for list_item in field_list:
            if list_item in validated_data:
                setattr(instance, list_item, validated_data.get(list_item))
        instance.save()
        return instance

    def get_grouptype(self, obj):
        return obj.get_grouptype()


class GroupAccountDataSerializer(serializers.ModelSerializer):

    avatar_photo = ProfilePictureSerializer(read_only=True)
    account_name = serializers.CharField(read_only=True, source='get_short_name')
    group_id = serializers.CharField(read_only=True, source="vanity_urls.name")

    class Meta:
        model = StargramzUser
        fields = ['group_id', 'account_name', 'avatar_photo']


class GroupTypeListSerializer(serializers.ModelSerializer):

    exclude_condition = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = self.context.get("user")
        if user:
            self.exclude_condition = {'account_user__user_id': user.id}

    groups = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = GroupType
        fields = ['group_name', 'groups']

    def get_groups(self, obj):
        user = StargramzUser.objects.select_related(
            'avatar_photo').prefetch_related('vanity_urls', 'group_account', 'account_user').filter(
            group_account__admin_approval=True, group_account__group_type=obj
        ).exclude(**self.exclude_condition)
        serializers_data = GroupAccountDataSerializer(user, many=True).data
        return serializers_data


class GroupTypeSerializer(serializers.ModelSerializer):

    class Meta:
        model = GroupType
        fields = ['group_name', 'id']


class GroupListSerializer(serializers.ModelSerializer):
    group_follow = serializers.SerializerMethodField(read_only=True, required=False)
    avatar_photo = ProfilePictureSerializer(read_only=True)
    featured_photo = ProfilePictureSerializer(read_only=True)
    user_id = serializers.SerializerMethodField(read_only=True)
    celebrity_profession = ProfessionTitleSerializer(read_only=True, many=True)
    has_group_account = HasGroupAccountSerializer(read_only=True)
    group_type = serializers.CharField(read_only=True, source="group_account.group_type")
    rate = serializers.IntegerField(read_only=True, source="celebrity_user.rate")
    in_app_price = serializers.FloatField(read_only=True, source="celebrity_user.in_app_price")


    def get_user_id(self, obj):
        try:
            return VanityUrl.objects.values_list('name', flat=True).get(user=obj.id)
        except Exception:
            return ''

    def get_group_follow(self, obj):
            try:
                if self.context['request'].user:
                    user = StargramzUser.objects.get(username=self.context['request'].user)
                    CelebrityFollow.objects.get(fan=user, celebrity_id=obj.id)
                    return True
                else:
                    return False
            except Exception:
                return False

    class Meta:
        model = StargramzUser
        fields = ('group_follow', 'avatar_photo', 'get_short_name', 'first_name', 'featured_photo', 'user_id',
                  'celebrity_profession', 'has_group_account', 'group_type', 'rate', 'in_app_price')


class JoinGroupSerializer(serializers.ModelSerializer):

    account = serializers.CharField(required=True)

    class Meta:
        model = CelebrityGroupAccount
        fields = ('account', 'user', 'celebrity_invite')

    def validate(self, data):
        accounts_list = data.get('account')
        try:
            if accounts_list:
                accounts_list = accounts_list.split(',')
            data['account'] = [get_user_id(accounts.lstrip()) for accounts in accounts_list]
        except Exception:
            raise serializers.ValidationError({"error": "Invalid Group account"})
        return data

    def create(self, validated_data):
        accounts = validated_data.get('account')
        del validated_data['account']
        celebrity_accounts = []
        for account in accounts:
            celebrity_account, created = CelebrityGroupAccount.objects.update_or_create(
                user=validated_data.get('user'),
                account=account,
                defaults=validated_data
            )
            celebrity_accounts.append(celebrity_account)
        return celebrity_accounts


class JoinGroupCelebritySerializer(serializers.ModelSerializer):

    user = serializers.CharField(required=True)

    class Meta:
        model = CelebrityGroupAccount
        fields = ('account', 'user', 'approved')

    def validate(self, data):
        celebrity_list = data.get('user')
        try:
            if celebrity_list:
                celebrity_list = celebrity_list.split(',')
            data['user'] = [get_user_id(celebrity.lstrip()) for celebrity in celebrity_list]
        except Exception:
            raise serializers.ValidationError({"error": "Invalid Group account"})
        return data

    def create(self, validated_data):
        celebrity_list = validated_data.get('user')
        del validated_data['user']
        celebrities = []
        for celebrity in celebrity_list:
            celebrity_account, created = CelebrityGroupAccount.objects.update_or_create(
                user=celebrity,
                account=validated_data.get('account'),
                approved=True,
                celebrity_invite=True,
                defaults=validated_data
            )
            celebrities.append(celebrity_account)
        return celebrities


class SocialMediaSerializer(serializers.Serializer):

    facebook_url = serializers.URLField(required=False, allow_blank=True)
    twitter_url = serializers.URLField(required=False, allow_blank=True)
    youtube_url = serializers.URLField(required=False, allow_blank=True)
    instagram_url = serializers.URLField(required=False, allow_blank=True)

    class Meta:
        fields = ('facebook_url', 'twitter_url', 'youtube_url', 'instagram_url')


class SocialMediaLinkSerializer(serializers.ModelSerializer):

    class Meta:
        model = SocialMediaLinks
        fields = ('social_link_key', 'social_link_value')


class CelebrityGroupAccountSerializer(serializers.ModelSerializer):

    account = serializers.SerializerMethodField(read_only=True)
    celebrity = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CelebrityGroupAccount
        fields = ('account', 'celebrity', 'approved', 'celebrity_invite')

    def get_account(self, obj):
        try:
            vanity = VanityUrl.objects.get(user=obj.account).name
            return vanity
        except Exception:
            return None

    def get_celebrity(self, obj):
        return obj.user.get_short_name()


class GroupFollowSerializer(serializers.Serializer):
    follow = serializers.BooleanField(required=True)
    group = serializers.CharField(required=True)

    def validate(self, data):
        accounts_name = data.get('group')
        try:
            data['group'] = get_user_id(accounts_name)
        except Exception:
            raise serializers.ValidationError({"error": "Invalid Group account"})
        return data


class MemberListSerializer(serializers.ModelSerializer):
    celebrity_account = serializers.SerializerMethodField(read_only=True)
    avatar_photo = ProfilePictureSerializer(read_only=True)
    featured_photo = ProfilePictureSerializer(read_only=True)
    user_id = serializers.CharField(read_only=True, source="vanity_urls.name")
    celebrity_profession = ProfessionTitleSerializer(read_only=True, many=True)
    has_group_account = HasGroupAccountSerializer(read_only=True)
    group_type = serializers.CharField(read_only=True, source="group_account.group_type")


    class Meta:
        model = StargramzUser
        fields = ('celebrity_account', 'avatar_photo', 'get_short_name', 'first_name', 'featured_photo', 'user_id',
                  'celebrity_profession', 'has_group_account', 'group_type')

    def get_celebrity_account(self, obj):
        celebrity = self.context.get('request').GET.get("celebrity", None)
        # serialize groups of the current celebrity
        if celebrity:
            celebrity_account = CelebrityGroupAccount.objects.values('id', 'approved', 'celebrity_invite') \
                .filter(user=self.context.get('request').user, account=obj)
        # serialize celebrities of the current group
        else:
            celebrity_account = CelebrityGroupAccount.objects.values('id', 'approved', 'celebrity_invite')\
                .filter(user=obj, account=self.context.get('request').user)
        if celebrity_account:
            celebrity_account[0].update(id=hashids.encode(celebrity_account[0].get('id')))
        return celebrity_account


class CelebrityRepresentativeSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(required=False, allow_blank=True, max_length=120,
                                       error_messages={"max_length": "First Name must not exceed 120 character"})
    last_name = serializers.CharField(required=False, allow_blank=True, max_length=120,
                                      error_messages={"max_length": "Last Name must not exceed 120 character"})
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    country_code = serializers.CharField(required=False, allow_blank=True)
    email_notify = serializers.BooleanField(required=False, default=False)
    sms_notify = serializers.BooleanField(required=False, default=False)

    class Meta:
        model = Representative
        fields = ('celebrity', 'first_name', 'last_name', 'email', 'phone', 'email_notify', 'sms_notify',
                  'country_code')

    def create(self, validated_data):
        celebrity = validated_data.get('celebrity')
        representatives_number = Representative.objects.filter(celebrity=celebrity).count()
        if representatives_number >= 2:
            raise serializers.ValidationError("Maximum number of representatives")
        else:
            try:
                first_name = validated_data.get('first_name')
                last_name = validated_data.get('last_name')
                email = validated_data.get('email')
                phone = validated_data.get('phone')
                country_code = validated_data.get('country_code')
                email_notify = validated_data.get('email_notify')
                sms_notify = validated_data.get('sms_notify')
                representative = Representative.objects.create(
                    first_name=first_name, last_name=last_name,
                    email=email, phone=phone, email_notify=email_notify,
                    sms_notify=sms_notify, celebrity=celebrity, country_code=country_code
                )
                representative_email(celebrity, representative)
                return representative
            except Exception as e:
                raise serializers.ValidationError("Email already exist")

    def update(self, instance, validated_data):
        field_list = ['first_name', 'last_name', 'email', 'phone', 'email_notify', 'sms_notify', 'country_code']
        for list_item in field_list:
            if list_item in validated_data:
                setattr(instance, list_item, validated_data.get(list_item))
        instance.save()
        return instance


class CelebrityRepresentativeViewSerializer(serializers.ModelSerializer):
    representative_id = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Representative
        fields = ('representative_id', 'first_name', 'last_name', 'email', 'phone', 'email_notify', 'email_verified',
                  'sms_notify', 'sms_verified', 'country_code')

    def get_representative_id(self, obj):
        return hashids.encode(obj.id)


class ValidatePhoneNumberSerializer(serializers.Serializer):
    phone_regex = SerialValidator.RegexValidator(regex=r'^\+?1?\d{8,10}$', message="Phone number must be up to 10 digits.")
    country_code_regex = SerialValidator.RegexValidator(regex=r'^\+?1?\d{1,4}$', message="Country code up to 5 digits.")
    phone_number = serializers.IntegerField(required=True, validators=[phone_regex])
    country_code = serializers.CharField(required=True, validators=[country_code_regex])


class VerifyPhoneNumberSerializer(serializers.Serializer):
    phone_regex = SerialValidator.RegexValidator(regex=r'^\+?1?\d{8,10}$', message="Phone number must be up to 10 digits.")
    country_code_regex = SerialValidator.RegexValidator(regex=r'^\+?1?\d{1,4}$', message="Country code up to 5 digits.")
    verify_regex = SerialValidator.RegexValidator(regex=r'^[0-9]{4}$', message="Verification code up to 4 digits.")
    phone_number = serializers.IntegerField(required=True, validators=[phone_regex])
    country_code = serializers.CharField(required=True, validators=[country_code_regex])
    verification_code = serializers.CharField(required=True, validators=[verify_regex])
