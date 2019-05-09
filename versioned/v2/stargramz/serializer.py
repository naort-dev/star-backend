from rest_framework import serializers
from stargramz.serializer import StargramzVideoSerializer, OccasionSerializer, ReactionListingSerializer
from stargramz.models import Comment
from utilities.utils import encode_pk

class CommentSerializerV2(serializers.ModelSerializer):
    user_id = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Comment
        fields = ('user_id', 'comments')

    def get_user_id(self, obj):
        return encode_pk(obj.user.id)

class StargramzVideoSerializerV2(StargramzVideoSerializer):
    comments = serializers.SerializerMethodField(read_only=True)

    def get_comments(self, obj):
        try:
            comments = Comment.objects.filter(video_id=obj.id).order_by('-created_date')[0:3]
            comments = CommentSerializerV2(comments, many=True).data
            return comments
        except Exception:
            return []


class OccasionSerializerV2(OccasionSerializer):

    class Meta(OccasionSerializer.Meta):
        fields = ('id', 'title', 'occasion_image', 'relationships', 'type', 'other_check', 'template_type')


class ReactionListingSerializerV2(ReactionListingSerializer):
    booking_id = serializers.SerializerMethodField(read_only=True)

    class Meta(ReactionListingSerializer.Meta):
        fields = ReactionListingSerializer.Meta.fields + ('booking_id',)

    def get_booking_id(self, obj):
        return encode_pk(obj.booking.id)
