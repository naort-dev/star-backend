from rest_framework.routers import DefaultRouter
from .views import FeaturedVideoV2, OccasionListV2, ReactionsFullListing
from django.conf.urls import url

urlpatterns = [
    url(r'^occasion_list/$', OccasionListV2.as_view(), name='occasion_list-v2'),
]

router = DefaultRouter()
router.register(r'featured_videos', FeaturedVideoV2, base_name='featured video list')
router.register(r'reactions_full_listing/?(?P<pk>[0-9a-zA-Z-]{0,20})', ReactionsFullListing, base_name='reactions full listing')

urlpatterns = router.urls + urlpatterns
