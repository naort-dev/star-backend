from utilities.utils import encode_pk, get_pre_signed_get_url, get_s3_public_url, decode_pk
from rest_framework import serializers
from users.serializer import ProfessionSerializer, ProfessionFilterSerializer, ProfilePictureSerializer, \
    CelebrityRatingSerializerEncoder
from .models import CelebrityDisplay, HomePageVideo, VIDEO_TYPES, CelebrityDashboard
from users.serializer import UserSerializer
from users.models import CelebrityProfession, Profession, VanityUrl, StargramzUser, Celebrity, RecentActivity, ACTIVITY_TYPES
from config.models import Config
from django.db.models import F, Q
import datetime
import pytz
from versioned.v2.stargramz.serializer import StargramzRetrieveSerializerV2, ReactionListingSerializerV2, \
    TippingSerializerV2
from stargramz.serializer import CommentReplySerializer
from config.constants import *
import django.contrib.auth.password_validation as validators


class ProfessionSerializerV2(ProfessionSerializer):
    class Meta(ProfessionSerializer.Meta):
        fields = ('id', 'title', 'parent', 'description', 'child', 'file', 'order')


class ProfessionFilterSerializerV2(ProfessionFilterSerializer):
    class Meta(ProfessionFilterSerializer.Meta):
        fields = ('id', 'title', 'parent', 'description', 'child', 'file', 'order')


class SearchProfessionSerializer(serializers.Serializer):
    id = serializers.SerializerMethodField(read_only=True)
    title = serializers.CharField(read_only=True)

    def get_id(self, obj):
        return encode_pk(obj['id'])


class SearchCelebritySerializer(serializers.Serializer):
    user_id = serializers.SerializerMethodField(read_only=True)
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)
    nick_name = serializers.CharField(read_only=True)
    avatar_photo = serializers.CharField(read_only=True)
    image_url = serializers.CharField(read_only=True)
    thumbnail_url = serializers.CharField(read_only=True)
    professions = serializers.CharField(read_only=True)

    def get_user_id(self, obj):
        return encode_pk(obj['user_id'])


class SearchSerializer(serializers.Serializer):
    professions = SearchProfessionSerializer(many=True)
    celebrities = SearchCelebritySerializer(many=True)


class CelebrityDisplaySerializer(serializers.ModelSerializer):

    name = serializers.SerializerMethodField(read_only=True)
    avatar_photo = serializers.SerializerMethodField(read_only=True)
    professions = serializers.SerializerMethodField(read_only=True)
    rate = serializers.CharField(read_only=True, source="celebrity.celebrity_user.rate")
    in_app_price = serializers.CharField(read_only=True, source="celebrity.celebrity_user.in_app_price")
    id = serializers.IntegerField(read_only=True, source="order")
    celebrity_id = serializers.SerializerMethodField(read_only=True)
    celebrity_hash_id = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CelebrityDisplay
        fields = ('id', 'celebrity_hash_id', 'celebrity_id', 'name', 'avatar_photo', 'in_app_price', 'rate', 'professions')

    def get_name(self, obj):
        return obj.celebrity.get_short_name()

    def get_avatar_photo(self, obj):
        return ProfilePictureSerializer(obj.celebrity.avatar_photo).data

    def get_professions(self, obj):
        profession = CelebrityProfession.objects.values_list('profession', flat=True).filter(user_id=obj.celebrity.id)
        profession = Profession.objects.values_list('title', flat=True).filter(id__in=profession)
        return profession

    def get_celebrity_id(self, obj):
        try:
            return VanityUrl.objects.values_list('name', flat=True).get(user=obj.celebrity.id)
        except Exception:
            return ''

    def get_celebrity_hash_id(self, obj):
        try:
            return encode_pk(obj.celebrity.id)
        except Exception:
            return ''


class TrendingCelebritySerializer(UserSerializer):
    class Meta(UserSerializer.Meta):
        fields = ('id', 'first_name', 'last_name', 'nick_name', 'celebrity_user', 'images', 'celebrity_profession',
                  'avatar_photo', 'show_nick_name', 'get_short_name', 'featured_photo', 'user_id')


class HomePageVideoSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField(read_only=True)
    video_name = serializers.SerializerMethodField(read_only=True)
    video_type = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = HomePageVideo
        fields = ('id', 'video_name', 'url', 'video_type')

    def get_video_name(self, obj):
        return obj.video.name.split("/")[-1]

    def get_url(self, obj):
        try:
            config = Config.objects.get(key='home_page_videos')
            video = obj.video.name.split("/")[-1]
            video_url = get_pre_signed_get_url(video, config.value)
            return video_url
        except Exception:
            return ""

    def get_video_type(self, obj):
        return VIDEO_TYPES.get_key(obj.video_type)


class RegisterUserSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True, allow_blank=False)
    first_name = serializers.CharField(required=True, allow_blank=False)
    last_name = serializers.CharField(required=True, allow_blank=False)
    nick_name = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = StargramzUser
        fields = ('first_name', 'last_name', 'nick_name', 'email')
        depth = 1


class CelebrityApprovalSerializer(serializers.Serializer):
    reset_id = serializers.UUIDField(required=True, allow_null=False)

    def validate(self, data):
        reset_id = data.get('reset_id', '')
        try:
            user = StargramzUser.objects.get(reset_id=reset_id)
            celebrity = Celebrity.objects.get(user_id=user.id)
        except StargramzUser.DoesNotExist:
            raise serializers.ValidationError('Data not found')
        return celebrity, user


class CelebrityShareSerializer(serializers.Serializer):
    share_type = serializers.IntegerField(required=True)

    def validate(self, data):
        if data['share_type'] < 1 or data['share_type'] > 2:
            raise serializers.ValidationError('share_type must be 1 or 2')
        return data

    def save(self, user):
        try:
            dashboard = CelebrityDashboard.objects.get(user_id=user.id)
            if self.validated_data['share_type'] == 1:
                dashboard.profile_share_count = F('profile_share_count') + 1
                dashboard.last_profile_shared_at = datetime.datetime.now(pytz.UTC)
            elif self.validated_data['share_type'] == 2:
                dashboard.video_share_count = F('video_share_count') + 1
                dashboard.last_video_shared_at = datetime.datetime.now(pytz.UTC)
            dashboard.save()
        except:
            pass


class CelebrityDashboardSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CelebrityDashboard
        fields = '__all__'

    def get_user(self, obj):
        return encode_pk(obj.user.id)


class CelebrityRatingSerializerEncoderV2(CelebrityRatingSerializerEncoder):
    user = serializers.CharField(read_only=True, source="fan.get_short_name")
    user_image_url = serializers.SerializerMethodField(read_only=True)

    class Meta(CelebrityRatingSerializerEncoder.Meta):
        fields = CelebrityRatingSerializerEncoder.Meta.fields + ('created_date', 'user', 'user_image_url')

    def get_user_image_url(self, obj):
        config = PROFILE_IMAGES
        return get_s3_public_url(str(obj.fan.avatar_photo), config)


class RecentActivitySerializer(serializers.ModelSerializer):
    activity_from_user = serializers.CharField(read_only=True, source="activity_from_user.get_short_name")
    activity_to_user = serializers.CharField(read_only=True, source="activity_to_user.get_short_name")
    request = StargramzRetrieveSerializerV2(read_only=True)
    activity_type = serializers.SerializerMethodField(read_only=True)
    activity_details = serializers.SerializerMethodField(read_only=True)
    id = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = RecentActivity
        fields = ('id', 'activity_from_user', 'activity_to_user', 'request', 'activity_type', 'activity_details',
                  'created_date')

    def get_activity_type(self, obj):
        activity_types = dict(ACTIVITY_TYPES.choices())
        return activity_types[obj.activity_type]

    def get_activity_details(self, obj):
        if obj.activity_type == ACTIVITY_TYPES.comment:
            activity_details = CommentReplySerializer(obj.content_object, read_only=True).data
        elif obj.activity_type == ACTIVITY_TYPES.reaction:
            activity_details = ReactionListingSerializerV2(obj.content_object, read_only=True).data
        elif obj.activity_type == ACTIVITY_TYPES.tip:
            activity_details = TippingSerializerV2(obj.content_object, read_only=True).data
        elif obj.activity_type == ACTIVITY_TYPES.rating:
            activity_details = CelebrityRatingSerializerEncoderV2(obj.content_object, read_only=True).data

        return activity_details

    def get_id(self, obj):
        return encode_pk(obj.id)


class ActivityPublicVisibilitySerializer(serializers.ModelSerializer):
    activity = serializers.CharField(required=True)

    class Meta:
        model = RecentActivity
        fields = ('activity', 'activity_from_user', 'activity_to_user')

    def validate(self, data):
        try:
            activity = RecentActivity.objects.get(
                id=decode_pk(data.get('activity')),
                activity_to_user=data.get('activity_to_user')
            )
            data.update(
                {
                    'activity': activity,
                }
            )
        except:
            raise serializers.ValidationError('activity_id is invalid')

        return data

    def save(self, **kwargs):
        activity = self.validated_data['activity']
        if activity.public_visibility:
            activity.public_visibility = False
        else:
            activity.public_visibility = True
        activity.save()


class ContactSupportSerializerV2(serializers.Serializer):
    """
        Comments field serializer
    """

    comments = serializers.CharField(required=True)
    topic = serializers.CharField(required=True)


class ChangePasswordSerializerV2(serializers.Serializer):
    new_password = serializers.CharField(required=True, allow_blank=False, allow_null=False)

    def validate(self, data):
        new_password = data.get('new_password', '')
        try:
            validators.validate_password(new_password)
        except Exception as e:
            raise serializers.ValidationError(str(e))
        return data
