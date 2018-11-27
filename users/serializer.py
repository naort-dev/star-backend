import django.contrib.auth.password_validation as validators
from django.contrib.auth.models import update_last_login
from django.contrib.auth import authenticate
from django.core import exceptions
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from rest_framework.authtoken.models import Token
from utilities.konstants import INPUT_DATE_FORMAT, OUTPUT_DATE_FORMAT, ROLES
from config.models import Config
from config.constants import *
from .models import StargramzUser, SIGN_UP_SOURCE_CHOICES, Celebrity, Profession, UserRoleMapping, ProfileImage, \
    CelebrityAbuse, CelebrityProfession, CelebrityFollow, DeviceTokens, SettingsNotifications, FanRating, Referral,\
    VanityUrl, GroupAccount, GroupType, CelebrityGroupAccount, SocialMediaLinks
from .impersonators import IMPERSONATOR
from role.models import Role
from datetime import datetime, timedelta
from django.utils import timezone
from .constants import LINK_EXPIRY_DAY, ROLE_ERROR_CODE, EMAIL_ERROR_CODE, NEW_OLD_SAME_ERROR_CODE, \
    OLD_PASSWORD_ERROR_CODE, PROFILE_PHOTO_REMOVED, MAX_RATING_VALUE, MIN_RATING_VALUE, FIRST_NAME_ERROR_CODE
from utilities.utils import CustomModelSerializer, get_pre_signed_get_url, datetime_range, get_s3_public_url,\
    get_user_id, get_bucket_url
import re
from utilities.permissions import CustomValidationError, error_function
from rest_framework import status
from stargramz.models import Stargramrequest, STATUS_TYPES
from django.db.models import Q, Sum
from utilities.constants import BASE_URL
from .tasks import welcome_email
from payments.models import PaymentPayout
from hashids import Hashids
hashids = Hashids(min_length=8)


class ProfilePictureSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    photo = serializers.CharField(read_only=True)
    thumbnail = serializers.CharField(read_only=True)
    image_url = serializers.SerializerMethodField('get_s3_image_url')
    thumbnail_url = serializers.SerializerMethodField('get_s3_thumbnail_url')

    def __init__(self, *args, **kwargs):
        self.bucket_url = get_bucket_url()
        super().__init__(*args, **kwargs)

    class Meta:
        model = ProfileImage
        fields = ('id', 'image_url', 'thumbnail_url', 'photo', 'thumbnail')

    def get_s3_image_url(self, obj):
        config = PROFILE_IMAGES
        return '{}/{}'.format(self.bucket_url, config+obj.photo)

    def get_s3_thumbnail_url(self, obj):
        if obj.thumbnail is not None:
            config = PROFILE_IMAGES
            return '{}/{}'.format(self.bucket_url, config+obj.thumbnail)
        else:
            return None


class RoleDetailSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=True)
    role_code = serializers.CharField(required=True)
    role_name = serializers.CharField(required=True)
    is_complete = serializers.BooleanField(required=True)

    class Meta:
        model = UserRoleMapping


class RegisterSerializer(serializers.ModelSerializer):
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
        if StargramzUser.objects.filter(email=email).exists():
            raise serializers.ValidationError("The email has already been registered.")
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
                .get(referral_code=referral_code, referral_active=True)
            Referral.objects.create(referrer_id=referrer_id, referee=user, source="branch.io")
        except StargramzUser.DoesNotExist:
            pass
    return True


class LoginSerializer(serializers.ModelSerializer):
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

    def validate(self, data):
        user = authenticate(username=data.get('username'), password=data['password'])
        if user is not None:
            # the password verified for the user
            if user.is_active:
                (token, created) = Token.objects.get_or_create(user=user)  # token.key has the key
                user.authentication_token = token.key
                user.sign_up_source = SIGN_UP_SOURCE_CHOICES.regular
                user.save()
                update_last_login(None, user=user)
                return user
            else:
                raise serializers.ValidationError({"error": "Account is not active. Contact support!"})
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
                  'sign_up_source', 'role_details', 'profile_photo', 'nick_name', 'fb_id', 'gp_id', 'in_id', 'role',
                  'avatar_photo', 'show_nick_name', 'completed_fan_unseen_count', 'referral_code')

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
            else:
                user = StargramzUser.objects.get(username=email)
            if user.profile_photo != PROFILE_PHOTO_REMOVED:
                user.profile_photo = profile_photo
            user.sign_up_source = sign_up_source
            if nick_name:
                user.nick_name = nick_name
                user.show_nick_name = True
            user.save()
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
                                                    fb_id=fb_id, gp_id=gp_id, in_id=in_id)
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
    child = ProfessionChildSerializer(many=True, read_only=True)
    file = serializers.SerializerMethodField()

    def get_file(self, obj):
        if obj.file:
            return "%s media/ %s" % (BASE_URL, obj.file)
        return None

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

        return ProfessionSerializer(profession, many=True).data

    def get_file(self, obj):
        if obj.file:
            return "%s media/ %s" % (BASE_URL, obj.file)
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
        weekly_limits = validated_data.get('weekly_limits')
        profile_video = validated_data.get('profile_video')
        professions = validated_data.get('profession')
        availability = validated_data.get('availability')
        description = validated_data.get('description', '')
        charity = validated_data.get('charity', '')
        celebrity = Celebrity.objects.\
            create(rate=rate, weekly_limits=weekly_limits, profile_video=profile_video,
                   user=user_id, availability=availability, description=description, charity=charity)
        for profession in professions:
            CelebrityProfession.objects.create(user=user_id, profession_id=profession)
        return celebrity

    def update(self, instance, validated_data):
        if validated_data.get('profession'):
            professions = validated_data.get('profession')
            CelebrityProfession.objects.filter(user=instance.user_id).delete()
            for profession in professions:
                CelebrityProfession.objects.create(user_id=instance.user_id, profession_id=profession)
        field_list = ['rate', 'weekly_limits', 'availability', 'description', 'charity']
        for list_item in field_list:
            if list_item in validated_data:
                setattr(instance, list_item, validated_data.get(list_item))
        instance.save()

        return instance


class CelebrityProfessionSerializer(serializers.ModelSerializer):

    def __init__(self, *args, **kwargs):
        mains = {}
        professions = Profession.objects.filter(parent=None).values('title', 'id')
        for profession in professions:
            mains.update({profession['id']: profession['title']})
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
        return {'rate': str(int(value.rate)), 'rating': str(value.rating),
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

    class Meta:
        model = StargramzUser
        fields = ('id', 'first_name', 'last_name', 'nick_name', 'celebrity_user', 'images', 'celebrity_profession',
                  'celebrity_follow', 'avatar_photo', 'show_nick_name', 'get_short_name', 'featured_photo', 'user_id',
                  'group_type', 'has_group_account')


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
    user_id = serializers.SerializerMethodField(read_only=True)
    has_group_account = HasGroupAccountSerializer(read_only=True)
    group_type = serializers.CharField(read_only=True, source="group_account.group_type")

    def get_user_id(self, obj):
        try:
            return VanityUrl.objects.values_list('name', flat=True).get(user=obj.id)
        except Exception:
            return ''

    class Meta:
        model = StargramzUser
        fields = ('id', 'first_name', 'last_name', 'nick_name', 'get_short_name', 'celebrity_profession',
                  'avatar_photo', 'user_id', 'has_group_account', 'group_type')


class DeviceTokenSerializer(serializers.ModelSerializer):

    class Meta:
        model = DeviceTokens
        fields = ('device_type', 'device_id', 'device_token')


class NotificationSettingsSerializer(CustomModelSerializer):
    id = serializers.IntegerField(write_only=True)

    class Meta:
        model = SettingsNotifications
        fields = '__all__'


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
        choices=['profile_images', 'stargram_videos', 'authentication_videos']
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

    id = serializers.IntegerField(read_only=True)
    account_name = serializers.CharField(read_only=True, source='get_short_name')

    class Meta:
        model = StargramzUser
        fields = ['account_name', 'id']


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
                  'celebrity_profession', 'has_group_account', 'group_type')


class JoinGroupSerializer(serializers.ModelSerializer):

    account = serializers.CharField(required=True)

    class Meta:
        model = CelebrityGroupAccount
        fields = ('account', 'user', 'celebrity_invite')

    def validate(self, data):
        accounts_name = data.get('account')
        try:
            data['account'] = get_user_id(accounts_name)
        except Exception:
            raise serializers.ValidationError({"error": "Invalid Group account"})
        return data


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

    class Meta:
        model = CelebrityGroupAccount
        fields = ('approved', 'celebrity_invite')


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
        celebrity_account = CelebrityGroupAccount.objects.values('id', 'approved', 'celebrity_invite')\
            .filter(user=obj, account=self.context.get('request').user)
        if celebrity_account:
            celebrity_account[0].update(id=hashids.encode(celebrity_account[0].get('id')))
        return celebrity_account

