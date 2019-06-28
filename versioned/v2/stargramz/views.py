from stargramz.views import FeaturedVideo, OccasionList, StargramzRequest, RequestList, BookingFeedbackView, CommentsView
from .serializer import StargramzVideoSerializerV2, OccasionSerializerV2, ReactionListingSerializerV2,\
    StargramzSerializerV2, StargramzRetrieveSerializerV2, VideoFavoritesSerializer, VideoHideFromPublicSerializer,\
    ReactionSerializerV2, CommentSerializerSavingV2, MakeBookingPrivateSerializer, CelebrityRatingSerializerV2
from rest_framework.viewsets import GenericViewSet
from utilities.mixins import ResponseViewMixin
from stargramz.models import Reaction, Stargramrequest, STATUS_TYPES, FILE_TYPES
from utilities.pagination import CustomOffsetPagination
from rest_framework.views import APIView
from users.models import UserRoleMapping, ROLES, FanRating, Celebrity
from .utils import high_cancel_check
from utilities.authentication import CustomAuthentication
from rest_framework.permissions import IsAuthenticated
from utilities.permissions import CustomPermission
from job.tasks import generate_reaction_videos, generate_reaction_image
from utilities.utils import decode_pk, average_rate_calculate
from users.serializer import CelebrityRatingSerializerEncoder
from stargramz.tasks import booking_feedback_celebrity_notification
import datetime


class FeaturedVideoV2(FeaturedVideo):
    serializer_class = StargramzVideoSerializerV2

    def list(self, request):
        self.required_fields.append('comments')
        self.queryset = self.queryset.filter(
            stragramz_request__request_rating__fan_rate__gte=4.00,
            public_visibility=True
        )
        return FeaturedVideo.list(self, request)


class OccasionListV2(OccasionList):

    serializer = OccasionSerializerV2


class ReactionsFullListing(GenericViewSet, ResponseViewMixin):
    pagination_class = CustomOffsetPagination
    serializer_class = ReactionListingSerializerV2

    def list(self, request, pk):
        try:

            reactions = Reaction.objects\
                .filter(booking__celebrity__vanity_urls__name=pk, file_thumbnail__isnull=False).order_by('-created_date')
            page = self.paginate_queryset(reactions)
            serializer = self.get_serializer(page, many=True)
            return self.paginator.get_paginated_response(serializer.data, key_name='reactions-details')
        except Exception as e:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'EXCEPTION', str(e))


def update_booking_v2(obj, star_request, request):
    star_request.occasion_id = request.data['occasion']
    star_request.request_details = request.data['request_details']
    star_request.public_request = request.data['public_request']
    star_request.booking_title = request.data['booking_title']
    star_request.booking_statement = request.data['booking_statement']
    star_request.save()


class StargramzRequestV2(StargramzRequest):
    serializer = StargramzSerializerV2
    retrieve_serializer = StargramzRetrieveSerializerV2
    update_data_in_booking = update_booking_v2


class VideoFavoritesView(APIView, ResponseViewMixin):
    def post(self, request):
        request.data.update({'celebrity': request.user.id})
        serializer = VideoFavoritesSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return self.jp_response(s_code='HTTP_200_OK', data='success')
        else:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_CODE',
                                          self.error_msg_string(serializer.errors))


class RequestListV2(RequestList):
    serializer_class = StargramzRetrieveSerializerV2

    def get_serializer_context(self):
        return {"user": self.user}

    def list(self, request):
        """
        This listing is similar to the version one but more filtering parameters
        :param request:
        :return:
        """
        query_set = self.queryset.prefetch_related(
            'request_rating', 'booking_reaction', 'tip_payment', 'favorite_booking', 'activity_request'
        )

        mappings = UserRoleMapping.objects.get(user=request.user)

        role_list = {ROLES.celebrity: 'celebrity_id', ROLES.fan: 'fan_id', ROLES.group_account: 'fan_id'}

        user_role = request.GET['role'] if 'role' in request.GET else None
        role = user_role if user_role and user_role in ['fan_id', 'celebrity_id'] else role_list[mappings.role.code]

        if mappings.role.code == ROLES.celebrity:
            request.user.unseen_bookings = 0
            request.user.save()

        custom_filter = {role: request.user.id}
        query_set = query_set.filter(**custom_filter)

        # status filtering

        filter_by_status = request.GET.get("status")
        if filter_by_status:
            if filter_by_status == 'all':
                filter_by_status = '2, 3, 4, 5, 6'
            try:
                filter_by_status = filter_by_status.replace(" ", "")
                filter_by_status = filter_by_status.split(',')
                filter_by_status = [int(i) for i in filter_by_status]

                query_set = query_set.filter(request_status__in=filter_by_status)
            except Exception as e:
                return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_CODE', str(e))

        # parameters

        rated = request.GET.get('rated', False)
        comments = request.GET.get('comments', False)
        reactions = request.GET.get('reactions', False)
        tips = request.GET.get('tips', False)
        favorites = request.GET.get('favorites', False)
        oldest = request.GET.get('oldest', False)
        recent_activity = request.GET.get('recent_activity', False)

        try:
            if rated == 'true':
                query_set = query_set.filter(request_rating__fan_rate__gt=0)
            if comments == 'true':
                query_set = query_set.filter(request_video__comment_video__comments__isnull=False)
            if reactions == 'true':
                query_set = query_set.filter(booking_reaction__reaction_file__isnull=False)
            if tips == 'true':
                query_set = query_set.filter(tip_payment__amount__isnull=False)
            if favorites == 'true':
                query_set = query_set.filter(favorite_booking__celebrity__isnull=False)

            # sorting
            query_set = query_set.order_by('created_date') if oldest == 'true' else query_set.order_by('-created_date')
            query_set = query_set.order_by('-recent_activity_date') if recent_activity == 'true' else query_set
            query_set = query_set.distinct()
            self.user = request.user
            page = self.paginate_queryset(query_set)
            serializer = self.get_serializer(page, many=True)
            data = self.paginator.get_paginated_response(serializer.data, key_name='request_list')
            if filter_by_status and len(filter_by_status) == 1 and filter_by_status[0] == STATUS_TYPES.cancelled:
                data.data['data'].update(
                    {
                        'high_cancel': high_cancel_check(query_set)[0],
                        'high_cancel_count': high_cancel_check(query_set)[1]
                    }
                )
            return data
        except Exception as e:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'EXCEPTION', str(e))


class VideoHideFromPublic(APIView, ResponseViewMixin):
    authentication_classes = (CustomAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)

    def post(self, request):
        serializer = VideoHideFromPublicSerializer(data=request.data, context={'user': request.user})
        if serializer.is_valid():
            serializer.save()
            return self.jp_response(s_code='HTTP_200_OK', data='success')
        else:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_CODE', self.error_msg_string(serializer.errors))


class BookingFeedbackViewV2(BookingFeedbackView):
    reaction_serializer = ReactionSerializerV2
    rating_serializer = CelebrityRatingSerializerV2
    rating_serializer_encoder = CelebrityRatingSerializerEncoder

    def post(self, request):

        try:
            booking, celebrity = Stargramrequest.objects.values_list('id', 'celebrity')\
                .get(id=decode_pk(request.data['booking']))
        except Exception as e:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'EXCEPTION', str(e))

        request.data['user'] = request.user.id
        request.data['booking'] = booking
        request.data['celebrity'] = celebrity
        feeback_type = request.data.get('type', None)
        if feeback_type == 'rating':
            try:
                FanRating.objects.get(starsona=booking, fan=request.user)
            except Exception:
                rating = self.rating_serializer(data=request.data)
                if rating.is_valid():
                    rating.save()
                    fields = {
                        'fan_rate': rating.validated_data.get('fan_rate'),
                        'comments': rating.validated_data.get('comments', ''),
                        'reason': rating.validated_data.get('reason', ''),
                    }
                    booking_feedback_celebrity_notification.delay(booking, fields)
                else:
                    return self.jp_error_response(
                        'HTTP_400_BAD_REQUEST', 'INVALID_LOGIN', self.error_msg_string(rating.errors)
                    )
        elif feeback_type == 'reaction':
            try:
                Reaction.objects.get(booking=booking, user=request.user)
            except:
                reaction = self.reaction_serializer(data=request.data)
                if reaction.is_valid():
                    reaction.save()
                else:
                    return self.jp_error_response(
                        'HTTP_400_BAD_REQUEST', 'INVALID_LOGIN', self.error_msg_string(reaction.errors)
                    )
        else:
            return self.jp_error_response(
                'HTTP_400_BAD_REQUEST', 'INVALID_LOGIN', 'Type is in valid'
            )
        try:
            celebrity_user = Celebrity.objects.get(user_id=celebrity)
            average_rate_calculate(celebrity_user)
        except:
            pass

        return self.jp_response(s_code='HTTP_200_OK', data='success')


class CommentsViewV2(CommentsView):
    comment_adding_serializer = CommentSerializerSavingV2


class ReactionProcess(APIView, ResponseViewMixin):
    authentication_classes = (CustomAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)

    def post(self, request):
        try:
            reaction = Reaction.objects.get(
                booking=decode_pk(request.data.get('booking')),
                user=request.user
            )
            if reaction.file_type == FILE_TYPES.video:
                generate_reaction_videos.delay(reaction.id)
            elif reaction.file_type == FILE_TYPES.image:
                generate_reaction_image.delay(reaction.id)
        except Exception as e:
            print(str(e))
        return self.jp_response(s_code='HTTP_200_OK', data='success')


class MakeBookingPrivate(APIView, ResponseViewMixin):
    authentication_classes = (CustomAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)

    def post(self, request):
        serializer = MakeBookingPrivateSerializer(data=request.data, context={'user': request.user})
        if serializer.is_valid():
            serializer.save()
            return self.jp_response(s_code='HTTP_200_OK', data='success')
        else:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_CODE',
                                          self.error_msg_string(serializer.errors))
