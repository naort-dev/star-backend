"""stargramz URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url, include
from django.contrib import admin
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static
from utilities import utils, constants
from stargramz.views import play_video, profile_detail, request_detail, page_not_found, get_bucket_private_url, \
    invite_referral, play_reaction_video
from health.views import health
from users.celebrity_views import celebrity_representative_email_verification

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^$', TemplateView.as_view(template_name="home/index.html")),
    url(r'^applinks/set_weekly_limit', TemplateView.as_view(template_name="home/index.html")),
    url(r'^applinks/invite/(?P<referral_code>.+)$', invite_referral, name="Invite code"),
    url(r'^representative/email_verification/(?P<rep_id>[0-9a-zA-Z]{5,8})', celebrity_representative_email_verification),
    url(r'^applinks/reset$', TemplateView.as_view(template_name="home/index.html")),
    url(r'^(?P<id>[0-9a-zA-Z]{5,8})/$', play_video, name="play-video"),
    url(r'^reactions/(?P<id>[0-9a-zA-Z]{5,8})/$', play_reaction_video, name="play-reaction-video"),
    url(r'^private/video/(?P<vname>.+)$', get_bucket_private_url, name="get-bucket-url"),
    url(r'^video/(?P<id>[0-9a-zA-Z]{5,8})/$', play_video, name="play-video"),
    url(r'^applinks/profile/(?P<user_id>[-\w]+)/$', profile_detail, name="profile-details"),
    url(r'^applinks/request/(?P<role>[0-9a-zA-Z]{5})/(?P<request_id>[0-9a-zA-Z]{5,8})$', request_detail, name="request-details"),
    url(r'^api/v1/ajax/', include('ajaxadmin.urls')),
    url(r'^api/v1/user/', include('users.urls')),
    url(r'^api/v1/config/', include('config.urls')),
    url(r'^api/v1/news/', include('news.urls')),
    url(r'^api/v1/request/', include('stargramz.urls')),
    url(r'^api/v1/payments/', include('payments.urls')),
    url(r'^api/v1/notification/', include('notification.urls')),
    url(r'^apple-app-site-association$', utils.download_file, {'path': constants.IOS_UNIVERSAL_FILE_PATH}),
    url(r'^.well-known/assetlinks.json$', utils.download_file, {
        'path': constants.ANDROID_UNIVERSAL_FILE_PATH,
        'content_type':"application/json"
    }),
    url(r'^download/(?P<id>[0-9a-zA-Z]{5,8})$', utils.download_video),
    url(r'^download_reactions/(?P<id>[0-9a-zA-Z]{5,8})$', utils.download_reaction_file),
    url(r'^health', health),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

handler404 = page_not_found
handler400 = page_not_found
handler500 = page_not_found

