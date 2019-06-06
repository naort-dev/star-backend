from rest_framework import serializers
from stargramz.serializer import StargramzVideoSerializer, OccasionSerializer, ReactionListingSerializer,\
    StargramzSerializer, StargramzRetrieveSerializer
from stargramz.models import Comment, Stargramrequest, REQUEST_TYPES
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


class StargramzSerializerV2(StargramzSerializer):
    booking_statement = serializers.CharField(required=False)

    class Meta(StargramzSerializer.Meta):
        fields = StargramzSerializer.Meta.fields + ['booking_statement']

    def create(self, data):
        fan = data.get('fan')
        celebrity = data.get('celebrity')
        occasion = data.get('occasion')
        public_request = data.get('public_request')
        request_details = data.get('request_details')
        booking_title = data.get('booking_title')
        booking_statement = data.get('booking_statement')
        request_type = int(data.get('request_type')) if data.get('request_type', None) else REQUEST_TYPES.personalised_video
        stargramrequest = Stargramrequest.objects.create(fan=fan, celebrity=celebrity, booking_title=booking_title,
                                                         occasion=occasion, request_details=request_details,
                                                         request_type=request_type, public_request=public_request,
                                                         booking_statement=booking_statement)
        stargramrequest.save()
        return stargramrequest


class StargramzRetrieveSerializerV2(StargramzRetrieveSerializer):
    class Meta(StargramzRetrieveSerializer.Meta):
        fields = StargramzRetrieveSerializer.Meta.fields + ['booking_statement']
