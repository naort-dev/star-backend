from django.conf.urls import url
from rest_framework.routers import DefaultRouter

from .views import FilterProfessionsV2, ProfessionsV2

urlpatterns = [
    url(r'^professions/$', ProfessionsV2.as_view(), name='profession-v2'),
]

router = DefaultRouter()
router.register(r'filtered_professions', FilterProfessionsV2, base_name='filtered-profession-v2')

urlpatterns = router.urls + urlpatterns
