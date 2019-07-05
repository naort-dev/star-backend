from rest_framework import serializers
from stargramz.serializer import StargramzVideoSerializer, OccasionSerializer, ReactionListingSerializer,\
    StargramzSerializer, StargramzRetrieveSerializer, TippingSerializer, CommentReplySerializer, ReactionSerializer,\
    CommentSerializer
from stargramz.models import Comment, Stargramrequest, REQUEST_TYPES, StargramVideo, Reaction, VIDEO_STATUS, \
    STATUS_TYPES
from utilities.utils import encode_pk, decode_pk, get_bucket_url, get_s3_public_url
from .models import VideoFavorites
from payments.models import TipPayment, PaymentPayout, StarsonaTransaction, PAYOUT_STATUS
from config.models import Config
from config.constants import *
from users.models import FanRating
import datetime


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
    """
        When calling this serializer it requires the user object in the context
    """
    comments = serializers.SerializerMethodField(read_only=True)
    tip_amount = serializers.SerializerMethodField(read_only=True)
    reaction_count = serializers.SerializerMethodField(read_only=True)
    video_thumbnail = serializers.SerializerMethodField(read_only=True)
    video_created_date = serializers.SerializerMethodField(read_only=True)
    fund_payed_out = serializers.SerializerMethodField(read_only=True)
    video_favorite = serializers.SerializerMethodField(read_only=True)
    video_visibility = serializers.SerializerMethodField(read_only=True)
    has_reaction = serializers.SerializerMethodField(read_only=True)
    has_comment = serializers.SerializerMethodField(read_only=True)
    has_rating = serializers.SerializerMethodField(read_only=True)
    fan_first_name = serializers.CharField(read_only=True, source="fan.first_name")
    celebrity_first_name = serializers.CharField(read_only=True, source="celebrity.first_name")
    celebrity_average_response_time = serializers.SerializerMethodField(read_only=True)

    class Meta(StargramzRetrieveSerializer.Meta):
        fields = StargramzRetrieveSerializer.Meta.fields + [
            'comments', 'tip_amount', 'reaction_count', 'video_thumbnail', 'video_created_date', 'fund_payed_out',
            'video_favorite', 'video_visibility', 'has_reaction', 'has_comment', 'has_rating', 'celebrity_first_name',
            'fan_first_name', 'celebrity_average_response_time'
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
            except:
                return {
                    "payed_out_amount": None,
                    "payed_out_date": None
                }
        else:
            return None

    def get_video_favorite(self, obj):
        from versioned.v2.stargramz.models import VideoFavorites
        try:
            VideoFavorites.objects.get(booking_id=obj.id, celebrity=self.context['user'])
            return True
        except:
            return False

    def get_video_visibility(self, obj):
        try:
            video = StargramVideo.objects.get(stragramz_request_id=obj.id)
            return video.public_visibility
        except:
            return None

    def get_has_reaction(self, obj):
        try:
            Reaction.objects.get(booking_id=obj.id, user_id=self.context['user'].id)
        except:
            return False
        else:
            return True

    def get_has_comment(self, obj):
        try:
            video = StargramVideo.objects.get(stragramz_request_id=obj.id)
            if Comment.objects.filter(video_id=video.id, user_id=self.context['user'].id).count() > 0:
                return True
            else:
                return False
        except:
            return False

    def get_has_rating(self, obj):
        from users.models import FanRating
        try:
            FanRating.objects.get(starsona_id=obj.id, fan_id=self.context['user'].id)
        except:
            return False
        else:
            return True

    def get_celebrity_average_response_time(self, obj):
        from versioned.v2.users.views import UserDetailsV2
        average_response_time, avg_response_value = UserDetailsV2.average_response_time(UserDetailsV2, obj.celebrity.id)
        return average_response_time


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


class ReactionSerializerV2(ReactionSerializer):

    class Meta(ReactionSerializer.Meta):
        fields = ('booking', 'reaction_file', 'file_type', 'user')

    def create(self, validated_data):
        try:
            Reaction.objects.create(
                booking=validated_data.get('booking'),
                user=validated_data.get('user'),
                file_type=validated_data.get('file_type'),
                reaction_file=validated_data.get('reaction_file'),
            )
        except Exception as e:
            print(str(e))
        return True


class CommentSerializerSavingV2(CommentSerializer):

    def save(self):
        request = Stargramrequest.objects.get(request_video=self.validated_data['video'])
        if request.celebrity.id == self.validated_data['user'].id:
            super().save()
        else:
            comments = self.Meta.model.objects.filter(
                user_id=self.validated_data['user'].id, video=self.validated_data['video']).count()
            if comments == 0:
                super().save()
            else:
                raise serializers.ValidationError('the user already has a comment')


class MakeBookingPrivateSerializer(serializers.Serializer):
    booking = serializers.CharField(required=True)
    public = serializers.BooleanField(required=True)

    def validate(self, data):
        try:
            data.update(
                {
                    'booking': Stargramrequest.objects.get(
                        id=decode_pk(data.get('booking')),
                        fan_id=self.context['user'].id
                    )
                }
            )

        except:
            raise serializers.ValidationError('booking id is incorrect')
        return data

    def save(self):
        self.validated_data['booking'].public_request = self.validated_data['public']
        self.validated_data['booking'].save()


class CelebrityRatingSerializerV2(serializers.Serializer):
    comments = serializers.CharField(required=False, allow_blank=True)
    user = serializers.IntegerField(required=True)
    celebrity = serializers.IntegerField(required=True)
    booking = serializers.IntegerField(required=True)
    reason = serializers.CharField(required=False, allow_blank=True)
    fan_rate = serializers.DecimalField(required=False, max_digits=4, decimal_places=2, allow_null=True)

    def validate(self, data):
        user = data.get('user')
        booking = data.get('booking')
        if FanRating.objects.filter(starsona_id=booking, fan_id=user).count() > 0:
            raise serializers.ValidationError('This user already rated this booking')
        return data

    def save(self):
        rating = FanRating.objects.create(
            fan_id=self.validated_data['user'], celebrity_id=self.validated_data['celebrity'],
            starsona_id=self.validated_data['booking'], comments=self.validated_data['comments'],
            reason=self.validated_data['reason'], fan_rate=self.validated_data['fan_rate'])
        return rating
