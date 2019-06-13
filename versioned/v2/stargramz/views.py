from stargramz.views import FeaturedVideo, OccasionList, StargramzRequest, RequestList
from .serializer import StargramzVideoSerializerV2, OccasionSerializerV2, ReactionListingSerializerV2,\
    StargramzSerializerV2, StargramzRetrieveSerializerV2, VideoFavoritesSerializer
from rest_framework.viewsets import GenericViewSet
from utilities.mixins import ResponseViewMixin
from stargramz.models import Reaction, Stargramrequest
from utilities.pagination import CustomOffsetPagination
from rest_framework.views import APIView
from users.models import UserRoleMapping, ROLES


class FeaturedVideoV2(FeaturedVideo):
    serializer_class = StargramzVideoSerializerV2

    def list(self, request):
        self.required_fields.append('comments')
        self.queryset = self.queryset.filter(stragramz_request__request_rating__fan_rate__gte=4.00)
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

    def list(self, request):
        """
        This listing is similar to the version one but more filtering parameters
        :param request:
        :return:
        """
        query_set = self.queryset.prefetch_related('request_rating', 'booking_reaction', 'tip_payment', 'favorite_booking')

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

        try:
            if rated:
                query_set = query_set.filter(request_rating__fan_rate__gt=0)
            if comments:
                query_set = query_set.filter(request_video__comment_video__comments__isnull=False)
            if reactions:
                query_set = query_set.filter(booking_reaction__reaction_file__isnull=False)
            if tips:
                query_set = query_set.filter(tip_payment__amount__isnull=False)
            if favorites:
                query_set = query_set.filter(favorite_booking__celebrity__isnull=False)

            # sorting

            if oldest:
                query_set = query_set.order_by('-created_date')
            else:
                query_set = query_set.order_by('created_date')

            page = self.paginate_queryset(query_set.distinct())
            serializer = self.get_serializer(page, many=True)
            return self.paginator.get_paginated_response(serializer.data, key_name='request_list')
        except Exception as e:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'EXCEPTION', str(e))
