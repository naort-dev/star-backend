from rest_framework import serializers
from .models import Occasion, Stargramrequest, StargramVideo, OccasionRelationship, ReportAbuse, REQUEST_TYPES, \
    Comment, Reaction, FILE_TYPES, ReactionAbuse
from config.models import Config
from config.constants import *
import json
from utilities.utils import CustomModelSerializer, get_pre_signed_get_url, get_s3_public_url, get_bucket_url
from .constants import REQUEST_STATUS_CHOICES, REQUEST_EDIT_ALLOWED_TIME
from utilities.constants import BASE_URL, SHORT_BASE_URL
from payments.models import StarsonaTransaction
from django.utils import timezone
import datetime
from users.serializer import ProfilePictureSerializer, CelebrityRatingSerializer, CelebrityProfessionSerializer
from users.models import ProfileImage, FanRating, CelebrityProfession, StargramzUser, CelebrityFollow, VanityUrl
from payments.models import StarsonaTransaction, TipPayment
from django.db.models import Q
from hashids import Hashids
hashids = Hashids(min_length=8)


class OccasionRelationshipSerializer(serializers.ModelSerializer):

    class Meta:
        model = OccasionRelationship
        fields = ('id', 'title')

class OccasionCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Occasion
        fields = ['id','title']

class OccasionSerializer(serializers.ModelSerializer):
    # data = serializers.SerializerMethodField('get_json_data')
    occasion_image = serializers.SerializerMethodField()
    relationships = OccasionRelationshipSerializer(many=True, read_only=True)

    class Meta:
        model = Occasion
        fields = ['id', 'title', 'occasion_image', 'relationships', 'type', 'other_check']

    def get_occasion_image(self, obj):
        if obj.occasion_image:
            return "%smedia/%s" % (BASE_URL, obj.occasion_image)
        return None


class StargramzVideoSerializer(CustomModelSerializer):

    def __init__(self, *args, **kwargs):
        self.bucket_url = get_bucket_url()
        super().__init__(*args, **kwargs)

    first_name = serializers.CharField(read_only=True, source="stragramz_request.celebrity.first_name")
    last_name = serializers.CharField(read_only=True, source="stragramz_request.celebrity.last_name")
    full_name = serializers.CharField(read_only=True, source="stragramz_request.celebrity.get_short_name")
    fan_name = serializers.CharField(read_only=True, source="stragramz_request.fan.get_short_name")
    celebrity_id = serializers.IntegerField(read_only=True, source="stragramz_request.celebrity.id")
    booking_id = serializers.SerializerMethodField(read_only=True)
    booking_type = serializers.IntegerField(read_only=True, source="stragramz_request.request_type")
    avatar_photo = ProfilePictureSerializer(read_only=True, source="stragramz_request.celebrity.avatar_photo")
    fan_avatar_photo = ProfilePictureSerializer(read_only=True, source="stragramz_request.fan.avatar_photo")
    professions = CelebrityProfessionSerializer(read_only=True, source="stragramz_request.celebrity.celebrity_profession", many=True)
    booking_title = serializers.CharField(read_only=True, source="stragramz_request.booking_title")
    video_status = serializers.SerializerMethodField(read_only=True)
    status = serializers.SerializerMethodField(read_only=True)
    s3_video_url = serializers.SerializerMethodField(read_only=True)
    s3_thumbnail_url = serializers.SerializerMethodField(read_only=True)
    video_url = serializers.SerializerMethodField(read_only=True)
    following = serializers.SerializerMethodField(read_only=True)
    video_id = serializers.SerializerMethodField(read_only=True)
    fan_rate = serializers.SerializerMethodField(read_only=True)
    occasion = serializers.CharField(read_only=True, source="stragramz_request.occasion.title")
    user_id = serializers.CharField(read_only=True, source="stragramz_request.celebrity.vanity_urls.name")
    question_answer_videos = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = StargramVideo
        fields = '__all__'

    def get_booking_id(self, obj):
        return hashids.encode(obj.stragramz_request_id)

    def get_video_id(self, obj):
        return hashids.encode(obj.id)

    def get_video_url(self, obj):
        return SHORT_BASE_URL + 'video/' + hashids.encode(obj.id)

    def get_status(self, obj):
        return False if obj.status == 3 else True

    def get_video_status(self, obj):
        return obj.status

    def get_s3_video_url(self, obj):
        return '{}private/video/{}.mp4?v=2.1'.format(BASE_URL, hashids.encode(obj.id))

    def get_s3_thumbnail_url(self, obj):
        if obj.thumbnail is not None:
            config = STARGRAM_VIDEO_THUMB
            return '{}/{}'.format(self.bucket_url, config + obj.thumbnail)

    def get_question_answer_videos(self, obj):
        if obj.stragramz_request.request_type == 3:

            try:
                question, answer = StargramVideo.objects.filter(
                   stragramz_request_id=obj.stragramz_request_id,
                   status__in=[4, 5]
                ).values_list('video', 'height', 'width', 'thumbnail', 'id').order_by('status')
                return {
                    'question': '{}private/video/{}.mp4?v=2.1'.format(BASE_URL, hashids.encode(question[4])),
                    'question_thumb': '{}/{}'.format(self.bucket_url, STARGRAM_VIDEO_THUMB + question[3]),
                    'answer': '{}private/video/{}.mp4?v=2.1'.format(BASE_URL, hashids.encode(answer[4])),
                    'answer_thumb': '{}/{}'.format(self.bucket_url, STARGRAM_VIDEO_THUMB + answer[3]),
                    'question_width': question[2],
                    'question_height': question[1],
                    'answer_width': answer[2],
                    'answer_height': answer[1],
                }
            except Exception as e:
                return None
        else:
            return None

    def get_following(self, obj):
        if self.context['request'].user.is_authenticated:
            try:
                user = StargramzUser.objects.get(username=self.context['request'].user)
                try:
                    CelebrityFollow.objects.get(fan=user, celebrity_id=obj.stragramz_request.celebrity_id)
                    return True
                except CelebrityFollow.DoesNotExist:
                    return False
            except StargramzUser.DoesNotExist:
                return False
        return False

    def get_fan_rate(self, obj):
        try:
            fan_rate = FanRating.objects.values_list('fan_rate', flat=True).get(starsona=obj.stragramz_request)
        except Exception:
            return None
        return fan_rate


class StargramzSerializer(serializers.ModelSerializer):
    from_audio_file = serializers.FileField(required=False)
    to_audio_file = serializers.FileField(required=False)
    request_video = StargramzVideoSerializer(read_only=True, many=True, fields=[
        's3_thumbnail_url', 's3_video_url', 'video_url', 'status', 'video_status', 'width', 'height', 'video_id',
        'comments_count', 'read_status'
    ])
    avatar_photo = serializers.SerializerMethodField(read_only=True)
    fan_photo = serializers.SerializerMethodField(read_only=True)
    professions = serializers.SerializerMethodField(read_only=True)
    editable = serializers.SerializerMethodField(read_only=True)
    fan_rating = serializers.SerializerMethodField(read_only=True)
    celebrity_id = serializers.IntegerField(read_only=True, source="celebrity.id")
    occasion_type = serializers.IntegerField(read_only=True, source="occasion.type")
    charity = serializers.CharField(read_only=True, source="celebrity.celebrity_user.charity")
    order_details = serializers.SerializerMethodField(read_only=True)
    remove_audios = serializers.CharField(required=False, write_only=True)
    booking_title = serializers.CharField(required=True)
    created_date = serializers.SerializerMethodField(read_only=True)
    booking_id = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Stargramrequest
        fields = ['id', 'fan', 'celebrity', 'occasion', 'request_details', 'from_audio_file', 'to_audio_file',
                  'request_status', 'created_date', 'request_video', 'comment', 'avatar_photo', 'public_request',
                  'professions', 'editable', 'fan_rating', 'celebrity_id', 'occasion_type', 'charity', 'booking_id',
                  'order_details', 'fan_photo', 'occasion_id', 'remove_audios', 'request_type', 'booking_title']

    def create(self, data):
        fan = data.get('fan')
        celebrity = data.get('celebrity')
        occasion = data.get('occasion')
        public_request = data.get('public_request')
        request_details = data.get('request_details')
        booking_title = data.get('booking_title')
        request_type = int(data.get('request_type')) if data.get('request_type', None) else REQUEST_TYPES.personalised_video
        stargramrequest = Stargramrequest.objects.create(fan=fan, celebrity=celebrity, booking_title=booking_title,
                                                         occasion=occasion, request_details=request_details,
                                                         request_type=request_type, public_request=public_request)
        stargramrequest.save()
        return stargramrequest

    def get_booking_id(self, obj):
        """
            Return hashed booking ID
        """
        return hashids.encode(obj.id)

    def get_created_date(self, obj):
        """
            Return the last modified date
        """
        return obj.modified_date if obj.request_status in [5, 6] else obj.created_date

    def get_avatar_photo(self, obj):
        try:
            query = ProfileImage.objects.get(id=obj.celebrity.avatar_photo_id)
            serializer = ProfilePictureSerializer(query)
            return serializer.data
        except ProfileImage.DoesNotExist:
                return None

    def get_fan_photo(self, obj):
        try:
            query = ProfileImage.objects.get(id=obj.fan.avatar_photo_id)
            serializer = ProfilePictureSerializer(query)
            return serializer.data
        except ProfileImage.DoesNotExist:
            if obj.fan.profile_photo:
                image = obj.fan.profile_photo
                social_profile = {
                    'id': str(1),
                    'image_url': image,
                    'thumbnail_url': image,
                    'photo': image,
                    'thumbnail': image
                }
                return social_profile
            else:
                return None


    def get_order_details(self, obj):
        try:
            starsona_transaction = StarsonaTransaction.objects.get(starsona_id=obj.id)
            return {'order': starsona_transaction.order_id(), 'amount': int(starsona_transaction.amount)}
        except StarsonaTransaction.DoesNotExist:
            return {'order': '', 'amount': int(obj.celebrity.celebrity_user.rate)}

    def get_professions(self, obj):
        query = CelebrityProfession.objects.filter(user_id=obj.celebrity_id)\
            .select_related('profession')
        serializer = CelebrityProfessionSerializer(query, many=True)
        return serializer.data

    def get_editable(self, obj):

        if obj.request_status not in [0, 1]:
            return False

        try:
            edit_time = BOOKING_EDIT_TIME
        except Exception:
            edit_time = REQUEST_EDIT_ALLOWED_TIME

        try:
            transaction = StarsonaTransaction.objects.get(starsona_id=obj.id)
            if timezone.now() > transaction.created_date + datetime.timedelta(minutes=int(edit_time)):
                return False
            return True
        except StarsonaTransaction.DoesNotExist:
            return True

    def get_fan_rating(self, obj):
        if obj.request_status == 6:
            try:
                query = FanRating.objects.get(Q(fan_id=obj.fan_id) &
                                              Q(celebrity_id=obj.celebrity_id) &
                                              Q(starsona_id=obj.id))
                serializer = CelebrityRatingSerializer(query)
                return serializer.data
            except FanRating.DoesNotExist:
                return None
        return None

class StargramzRetrieveSerializer(StargramzSerializer):
    from_audio_file = serializers.SerializerMethodField()
    to_audio_file = serializers.SerializerMethodField()
    request_details = serializers.SerializerMethodField()
    fan = serializers.CharField(read_only=True, source="fan.get_short_name")
    celebrity = serializers.CharField(read_only=True, source="celebrity.get_short_name")
    occasion = serializers.CharField(read_only=True, source="occasion.title")
    occasion_id = serializers.IntegerField(read_only=True, source="occasion.id")

    def get_request_details(self, obj):
        if obj.request_details:
            return json.loads(obj.request_details)
        return None

    def get_from_audio_file(self, obj):
        if obj.from_audio_file:
            return get_pre_signed_get_url(obj.from_audio_file, '')
        return None

    def get_to_audio_file(self, obj):
        if obj.to_audio_file:
            return get_pre_signed_get_url(obj.to_audio_file, '')
        return None


class TransactionStargramzSerializer(serializers.ModelSerializer):
    request_details = serializers.SerializerMethodField()
    occasion = serializers.CharField(read_only=True, source="occasion.title")
    fan = serializers.CharField(read_only=True, source="fan.get_short_name")

    class Meta:
        model = Stargramrequest
        fields = ('id', 'fan', 'occasion', 'request_details', 'booking_title')

    def get_request_details(self, obj):
        if obj.request_details:
            return json.loads(obj.request_details)
        return None


class RequestStatusSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=True, allow_null=False)
    status = serializers.ChoiceField(allow_blank=False, required=True, choices=REQUEST_STATUS_CHOICES)
    comment = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class AudioFileSerializer(serializers.ModelSerializer):
    from_audio_file = serializers.FileField(required=False)
    to_audio_file = serializers.FileField(required=False)

    class Meta:
        model = Stargramrequest
        fields = ('id', 'from_audio_file', 'to_audio_file')


class ReportAbuseSerializer(serializers.ModelSerializer):

    class Meta:
        model = ReportAbuse
        fields = ('request', 'comments', 'reported_by')


class CommentSerializer(serializers.ModelSerializer):
    video = serializers.CharField(required=True)

    def validate_video(self, value):
        try:
            video = hashids.decode(value)[0]
            return StargramVideo.objects.get(pk=video)
        except Exception:
            raise serializers.ValidationError("Invalid Video")

    class Meta:
        model = Comment
        fields = ('user', 'comments', 'video', 'reply')


class CommentUser(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = StargramzUser
        fields = ('image_url', 'get_short_name',)

    def get_image_url(self, obj):
        config = PROFILE_IMAGES
        return get_s3_public_url(str(obj.avatar_photo), config)


class CommentReplySerializer(serializers.ModelSerializer):
    user = CommentUser(read_only=True)

    class Meta:
        model = Comment
        fields = ('id', 'user', 'comments', 'created_date')


class FilesSerializer(serializers.Serializer):
    file_type = serializers.ChoiceField(allow_blank=False, required=True, choices=FILE_TYPES.choices())
    reaction_file = serializers.CharField(required=True)

    class Meta:
        fields = ('file_type', 'reaction_file',)


class ReactionSerializer(serializers.ModelSerializer):
    files = FilesSerializer(many=True)

    class Meta:
        model = Reaction
        fields = ('booking', 'files', 'user')

    def create(self, validated_data):
        from job.tasks import generate_reaction_videos, generate_reaction_image
        files = validated_data.get('files')
        for file in files:
            try:
                reaction = Reaction.objects.create(
                    booking=validated_data.get('booking'),
                    user=validated_data.get('user'),
                    file_type=file.get('file_type'),
                    reaction_file=file.get('reaction_file'),
                )
                if file.get('file_type') == 2:
                    generate_reaction_videos.apply_async(
                        (reaction.id,),
                        eta=datetime.datetime.utcnow() + datetime.timedelta(minutes=5)
                    )
                elif file.get('file_type') == 1:
                    generate_reaction_image.apply_async(
                        (reaction.id,),
                        eta=datetime.datetime.utcnow() + datetime.timedelta(minutes=5)
                    )
            except Exception as e:
                print(str(e))
        return True


class ReactionListingSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField(read_only=True)
    file_type = serializers.ChoiceField(allow_blank=False, required=True, choices=FILE_TYPES.choices())
    reaction_file_url = serializers.SerializerMethodField(read_only=True)
    reaction_thumbnail_url = serializers.SerializerMethodField(read_only=True)
    share_url = serializers.SerializerMethodField(read_only=True)
    reaction_id = serializers.SerializerMethodField(read_only=True)

    def __init__(self, *args, **kwargs):
        self.bucket_url = get_bucket_url()
        super().__init__(*args, **kwargs)

    class Meta:
        model = Reaction
        fields = ('reaction_id', 'user_name', 'file_type', 'reaction_file', 'reaction_file_url', 'reaction_thumbnail_url', 'share_url')

    def get_user_name(self, obj):
        return obj.user.get_short_name()

    def get_reaction_file_url(self, obj):
        return "{}/reactions/{}".format(self.bucket_url, obj.reaction_file)

    def get_reaction_thumbnail_url(self, obj):
        if obj.file_thumbnail:
            return "{}/reactions/thumbnails/{}".format(self.bucket_url, obj.file_thumbnail)
        else:
            return None

    def get_share_url(self, obj):
        return "{}reaction/{}".format(BASE_URL, hashids.encode(obj.id))

    def get_reaction_id(self, obj):
        return hashids.encode(obj.id)


class TippingSerializer(serializers.ModelSerializer):

    class Meta:
        model = TipPayment
        fields = ('amount', 'comments')


class ReactionAbuseSerializer(serializers.ModelSerializer):

    class Meta:
        model = ReactionAbuse
        fields = ('reaction', 'comments', 'reported_by')
