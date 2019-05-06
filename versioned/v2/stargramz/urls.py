from rest_framework.routers import DefaultRouter
from .views import FeaturedVideoV2

urlpatterns = [
]

router = DefaultRouter()
router.register(r'featured_videos', FeaturedVideoV2, base_name='featured video list')

urlpatterns = router.urls + urlpatterns
