from stargramz.views import FeaturedVideo, OccasionList
from .serializer import StargramzVideoSerializerV2, OccasionSerializerV2

class FeaturedVideoV2(FeaturedVideo):
    serializer_class = StargramzVideoSerializerV2

    def list(self, request):
        self.required_fields.append('comments')
        self.queryset = self.queryset.filter(stragramz_request__request_rating__fan_rate__gte=4.00)
        return FeaturedVideo.list(self, request)


class OccasionListV2(OccasionList):

    serializer = OccasionSerializerV2
