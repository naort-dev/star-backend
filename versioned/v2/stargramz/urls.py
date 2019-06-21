from rest_framework.routers import DefaultRouter
from .views import FeaturedVideoV2, OccasionListV2, ReactionsFullListing, StargramzRequestV2, RequestListV2,\
    VideoFavoritesView, VideoHideFromPublic
from django.conf.urls import url

urlpatterns = [
    url(r'^occasion_list/$', OccasionListV2.as_view(), name='occasion_list-v2'),
    url(r'^request_favorites/$', VideoFavoritesView.as_view(), name='request_favorites'),
    url(r'^video_hide_from_public/$', VideoHideFromPublic.as_view(), name='video_hide_from_public'),
]

router = DefaultRouter()
router.register(r'featured_videos', FeaturedVideoV2, base_name='featured video list')
router.register(r'reactions_full_listing/?(?P<pk>[0-9a-zA-Z-]{0,20})', ReactionsFullListing, base_name='reactions full listing')
router.register(r'stargramz', StargramzRequestV2, base_name='stragramz_request-v2')
router.register(r'request_list', RequestListV2, base_name='stargramz_list-v2')

urlpatterns = router.urls + urlpatterns
