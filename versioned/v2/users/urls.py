from django.conf.urls import url
from rest_framework.routers import DefaultRouter
from .views import FilterProfessionsV2, ProfessionsV2, CelebritySuggestionListV2, CelebrityDisplayView,\
    TrendingStars, Register

urlpatterns = [
    url(r'^professions/$', ProfessionsV2.as_view(), name='profession-v2'),
    url(r'^fan/suggestion_list', CelebritySuggestionListV2.as_view(), name='celebrity_suggestion_list-v2'),
    url(r'^celebrity_display/$', CelebrityDisplayView.as_view(), name='celebrity-display'),
    url(r'^trending_stars/$', TrendingStars.as_view(), name='trending_stars'),
    url(r'^register/$', Register.as_view(), name='register-v2'),
]

router = DefaultRouter()
router.register(r'filtered_professions', FilterProfessionsV2, base_name='filtered-profession-v2')

urlpatterns = router.urls + urlpatterns
