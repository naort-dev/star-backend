from django.conf.urls import url, include
from .views import OccasionList, StargramzRequest, StargramzVideo, FeaturedVideo, OtherRelationship,\
    RequestList, ChangeRequestStatus, RequestReportAbuse, CommentsView
from rest_framework.routers import DefaultRouter


urlpatterns = [
    url(r'^occasion_list/$', OccasionList.as_view(), name='occasion_list'),
    url(r'^other_relation/$', OtherRelationship.as_view(), name='other_relation'),
    url(r'^change_request_status/$', ChangeRequestStatus.as_view(), name='change_request_status'),
    url(r'^report_abuse/$', RequestReportAbuse.as_view(), name='report-abuse'),
    url(r'^comments/$', CommentsView.as_view(), name='comments'),
    url(r'^comments/(?P<pk>[0-9a-zA-Z]{5,8})/$', CommentsView.as_view(), name='comment-details'),
]

router = DefaultRouter()
router.register(r'stargramz_video', StargramzVideo, base_name='stragramz_request')
router.register(r'featured_videos', FeaturedVideo, base_name='featured video list')
router.register(r'stargramz', StargramzRequest, base_name='stragramz_request')
router.register(r'request_list', RequestList, base_name='stargramz_list')

urlpatterns = urlpatterns + router.urls
