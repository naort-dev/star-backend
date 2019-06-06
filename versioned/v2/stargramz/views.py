from stargramz.views import FeaturedVideo, OccasionList, StargramzRequest
from .serializer import StargramzVideoSerializerV2, OccasionSerializerV2, ReactionListingSerializerV2,\
    StargramzSerializerV2, StargramzRetrieveSerializerV2
from rest_framework.viewsets import GenericViewSet
from utilities.mixins import ResponseViewMixin
from stargramz.models import Reaction
from utilities.pagination import CustomOffsetPagination


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
