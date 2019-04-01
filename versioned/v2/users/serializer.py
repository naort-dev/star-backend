from utilities.utils import encode_pk
from rest_framework import serializers
from users.serializer import ProfessionSerializer, ProfessionFilterSerializer, ProfilePictureSerializer
from .models import CelebrityDisplay
from users.serializer import UserSerializer


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
    rate = serializers.CharField(read_only=True, source="celebrity.celebrity_user.rate")
    in_app_price = serializers.CharField(read_only=True, source="celebrity.celebrity_user.in_app_price")

    class Meta:
        model = CelebrityDisplay
        fields = ('id', 'name', 'avatar_photo', 'in_app_price', 'rate')

    def get_name(self, obj):
        return obj.celebrity.get_short_name()

    def get_avatar_photo(self, obj):
        return ProfilePictureSerializer(obj.celebrity.avatar_photo).data


class TrendingCelebritySerializer(UserSerializer):
    class Meta(UserSerializer.Meta):
        fields = ('id', 'first_name', 'last_name', 'nick_name', 'celebrity_user', 'images', 'celebrity_profession',
                  'avatar_photo', 'show_nick_name', 'get_short_name', 'featured_photo', 'user_id')
