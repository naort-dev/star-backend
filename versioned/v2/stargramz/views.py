from stargramz.views import FeaturedVideo, OccasionList
from .serializer import StargramzVideoSerializerV2, OccasionSerializerV2, ReactionListingSerializerV2
from rest_framework.viewsets import GenericViewSet
from utilities.mixins import ResponseViewMixin
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
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
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    pagination_class = CustomOffsetPagination
    serializer_class = ReactionListingSerializerV2

    def list(self, request):
        try:
            reactions = Reaction.objects\
                .filter(booking__celebrity_id=request.user.id, file_thumbnail__isnull=False).order_by('-created_date')
            page = self.paginate_queryset(reactions)
            serializer = self.get_serializer(page, many=True)
            return self.paginator.get_paginated_response(serializer.data, key_name='reactions-details')
        except Exception as e:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'EXCEPTION', str(e))
