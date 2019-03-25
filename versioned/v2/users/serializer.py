
from users.serializer import ProfessionSerializer, ProfessionFilterSerializer
from rest_framework import serializers
from utilities.utils import encode_pk


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
