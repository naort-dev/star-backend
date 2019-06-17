from django.conf.urls import url
from rest_framework.routers import DefaultRouter
from .views import FilterProfessionsV2, ProfessionsV2, CelebritySuggestionListV2, CelebrityDisplayView,\
    TrendingStars, Register, CelebrityListV2, UserDetailsV2, CelebrityManagementV2, StargramzAutocomplete, \
    ProfileImagesV2, CelebrityApproval, CelebrityShare, CelebrityDashboardView, DashboardUpdateView, RecentActivityView

urlpatterns = [
    url(r'^professions/$', ProfessionsV2.as_view(), name='profession-v2'),
    url(r'^fan/suggestion_list', CelebritySuggestionListV2.as_view(), name='celebrity_suggestion_list-v2'),
    url(r'^celebrity_display/$', CelebrityDisplayView.as_view(), name='celebrity-display'),
    url(r'^trending_stars/$', TrendingStars.as_view(), name='trending_stars'),
    url(r'^register/$', Register.as_view(), name='register-v2'),
    url(r'^celebrity_profile/$', CelebrityManagementV2.as_view(), name='celebrity_management-v2'),
    url(r'^user_autocomplete/$', StargramzAutocomplete.as_view(), name='user_autocomplete'),
    url(r'^profileimages/$', ProfileImagesV2.as_view(), name='profile_images-v2'),
    url(r'^celebrity_approval/$', CelebrityApproval.as_view(), name='celebrity_approval'),
    url(r'^celebrity_share/$', CelebrityShare.as_view(), name='celebrity_share'),
    url(r'^celebrity_dashboard/$', CelebrityDashboardView.as_view(), name='celebrity_dashboard'),
    url(r'^dashboard_update/$', DashboardUpdateView.as_view(), name='dashboard_update'),
]

router = DefaultRouter()
router.register(r'filtered_professions', FilterProfessionsV2, base_name='filtered-profession-v2')
router.register(r'fan/celebrity_list', CelebrityListV2, base_name='celebrity_list_v2')
router.register(r'user_details', UserDetailsV2, base_name='user_details-V2')
router.register(r'recent_activity', RecentActivityView, base_name='recent_activity')

urlpatterns = router.urls + urlpatterns
