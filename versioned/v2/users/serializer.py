from utilities.utils import encode_pk, get_pre_signed_get_url
from rest_framework import serializers
from users.serializer import ProfessionSerializer, ProfessionFilterSerializer, ProfilePictureSerializer
from .models import CelebrityDisplay, HomePageVideo
from users.serializer import UserSerializer
from users.models import CelebrityProfession, Profession, VanityUrl
from config.models import Config


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

    class Meta:
        model = HomePageVideo
        fields = ('id', 'video_name', 'url')

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
