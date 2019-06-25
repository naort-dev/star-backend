from rest_framework import serializers
from stargramz.serializer import StargramzVideoSerializer, OccasionSerializer, ReactionListingSerializer,\
    StargramzSerializer, StargramzRetrieveSerializer, TippingSerializer
from stargramz.models import Comment, Stargramrequest, REQUEST_TYPES, StargramVideo, Reaction, VIDEO_STATUS, STATUS_TYPES
from utilities.utils import encode_pk, decode_pk, get_bucket_url, get_s3_public_url
from .models import VideoFavorites
from payments.models import TipPayment, PaymentPayout, StarsonaTransaction, PAYOUT_STATUS
from config.models import Config
from config.constants import *


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
    user_image_url = serializers.SerializerMethodField(read_only=True)

    class Meta(ReactionListingSerializer.Meta):
        fields = ReactionListingSerializer.Meta.fields + ('booking_id', 'created_date', 'user_image_url',)

    def get_booking_id(self, obj):
        return encode_pk(obj.booking.id)

    def get_user_image_url(self, obj):
        config = PROFILE_IMAGES
        return get_s3_public_url(str(obj.user.avatar_photo), config)


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


class VideoFavoritesSerializer(serializers.ModelSerializer):
    booking = serializers.CharField(required=True)
    video = serializers.CharField(required=True)

    class Meta:
        model = VideoFavorites
        fields = ('booking', 'video', 'celebrity')

    def validate(self, data):
        try:
            booking = Stargramrequest.objects.get(id=decode_pk(data.get('booking')))
            video = StargramVideo.objects.get(id=decode_pk(data.get('video')))
            data.update(
                {
                    'booking': booking,
                    'video': video
                }
            )
        except:
            raise serializers.ValidationError('Booking_id or Video_id is invalid')

        return data

    def save(self, **kwargs):
        try:
            favorites = VideoFavorites.objects.get(
                celebrity_id=self.validated_data.get('celebrity'),
                booking=self.validated_data.get('booking'),
                video=self.validated_data.get('video')
            )
            favorites.delete()
        except:
            super().save(**kwargs)


class StargramzRetrieveSerializerV2(StargramzRetrieveSerializer):
    comments = serializers.SerializerMethodField(read_only=True)
    tip_amount = serializers.SerializerMethodField(read_only=True)
    reaction_count = serializers.SerializerMethodField(read_only=True)
    video_thumbnail = serializers.SerializerMethodField(read_only=True)
    video_created_date = serializers.SerializerMethodField(read_only=True)
    fund_payed_out = serializers.SerializerMethodField(read_only=True)

    class Meta(StargramzRetrieveSerializer.Meta):
        fields = StargramzRetrieveSerializer.Meta.fields + [
            'comments', 'tip_amount', 'reaction_count', 'video_thumbnail', 'video_created_date', 'fund_payed_out'
        ]

    def __init__(self, *args, **kwargs):
        self.stargram_video_thumb = Config.objects.get(key='stargram_video_thumb').value
        self.bucket_url = get_bucket_url()
        super().__init__(*args, **kwargs)

    def get_comments(self, obj):
        comment_count = Comment.objects.filter(video__stragramz_request_id=obj.id).count()
        return comment_count

    def get_tip_amount(self, obj):
        try:
            tip = TipPayment.objects.get(booking_id=obj.id)
            return tip.amount
        except:
            return 0.0

    def get_reaction_count(self, obj):
        reaction_count = Reaction.objects.filter(booking_id=obj.id).count()
        return reaction_count

    def get_video_thumbnail(self, obj):
        try:
            video = StargramVideo.objects.get(status=VIDEO_STATUS.completed, stragramz_request_id=obj.id)
            self.video_date = video.created_date
            if video.thumbnail is not None:
                config = self.stargram_video_thumb
                return '{}/{}'.format(self.bucket_url, config + video.thumbnail)
        except Exception as e:
            print(str(e))
            self.video_date = None
            return None

    def get_video_created_date(self, obj):
        return self.video_date

    def get_fund_payed_out(self, obj):
        if obj.request_status == STATUS_TYPES.completed:
            try:
                transaction = StarsonaTransaction.objects.get(starsona_id=obj.id, ambassador_transaction=False)
                payment = PaymentPayout.objects.get(
                    transaction_id=transaction.id,
                    referral_payout=False,
                    status=PAYOUT_STATUS.transferred
                )
                return {
                    "payed_out_amount": payment.fund_payed_out,
                    "payed_out_date": payment.modified_date
                }
            except Exception as e:
                print(str(e))
                return {
                    "payed_out_amount": None,
                    "payed_out_date": None
                }
        else:
            return None


class TippingSerializerV2(TippingSerializer):
    user = serializers.CharField(read_only=True, source="fan.get_short_name")
    user_image_url = serializers.SerializerMethodField(read_only=True)

    class Meta(TippingSerializer.Meta):
        fields = TippingSerializer.Meta.fields + ('created_date', 'user', 'user_image_url')

    def get_user_image_url(self, obj):
        config = PROFILE_IMAGES
        return get_s3_public_url(str(obj.fan.avatar_photo), config)


class VideoHideFromPublicSerializer(serializers.Serializer):
    video = serializers.CharField(required=True)

    def validate(self, data):
        try:
            data.update(
                {
                    'video': StargramVideo.objects.get(id=decode_pk(data.get('video')), stragramz_request__celebrity=self.context.get('user'))
                }
            )
        except Exception as e:
            print(str(e))
            raise serializers.ValidationError('video id is in valid')
        return data

    def save(self):
        video = self.validated_data.get('video')
        if video.public_visibility:
            video.public_visibility = False
        else:
            video.public_visibility = True
        video.save()
