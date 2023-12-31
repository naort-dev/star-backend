from django.conf.urls import url, include
from rest_framework.routers import DefaultRouter
from users.authenticate_views import UserRegister, UserLogin, EmailValidate, SocialSignup, ForgotPassword, \
    ResetPassword, Professions, ProfileImages, UserDetails, UserLogout, RemoveProfileImage, ChangePassword, \
    DeviceToken, NotificationSettings, ContactSupport, RoleUpdate, UpdateNotificationBadge, AlertFan, \
    ValidateSocialSignup, FilterProfessions, UpdateBookingCount, GetAWSSignedUrl, GetAWSSignedPostUrl, SocialMediaUrls, \
    ValidateMobile, VerifyMobile, TwitterIntegration, TwitterLogin
from users.group_views import GroupAccountList, GroupAccountsView, GroupTypesView, JoinGroupView, \
    GroupAccountProfileFollow, GetMembersList, GroupTypesListing
from .fan_views import CelebrityList, ApproveFan, CelebrityRate, CelebrityProfileFollow, CelebrityFanAbuse, \
    CelebritySuggestionList, FanFavouriteStars
from .celebrity_views import CelebrityManagement, NotifyAdmin, ReferralRequest, ReferralList, ReferralValidate, \
    CelebrityRepresentative

router = DefaultRouter()

urlpatterns = [
    url(r'^', include(router.urls)),
    url(r'^register/$', UserRegister.as_view(), name='register'),
    url(r'^login/$', UserLogin.as_view(), name='login'),
    url(r'^emailvalidate/$', EmailValidate.as_view(), name='email-validate'),
    url(r'^socialsignup/$', SocialSignup.as_view(), name='social-signup'),
    url(r'^forgotpassword/$', ForgotPassword.as_view(), name='forgot-password'),
    url(r'^resetpassword/$', ResetPassword.as_view(), name='reset-password'),
    url(r'^changepassword/$', ChangePassword.as_view(), name='change-password'),
    url(r'^professions/$', Professions.as_view(), name='profession'),
    url(r'^profileimages/$', ProfileImages.as_view(), name='profile-images'),
    url(r'^celebrity_profile/$', CelebrityManagement.as_view(), name='celebrity_profile'),
    url(r'^fan/approve/$', ApproveFan.as_view(), name='fan-approval'),
    url(r'^logout/$', UserLogout.as_view(), name='logout'),
    url(r'^fan/celebrity_rating/$', CelebrityRate.as_view(), name='rate_celebrity'),
    url(r'^fan/celebrity_follow/$', CelebrityProfileFollow.as_view(), name='celebrity_follow'),
    url(r'^fan/celebrity_abuse/$', CelebrityFanAbuse.as_view(), name='celebrity_abuse'),
    url(r'^fan/suggestion_list', CelebritySuggestionList.as_view(), name='celebrity_suggestion_list'),
    url(r'^notify_admin/$', NotifyAdmin.as_view(), name='notify-admin'),
    url(r'^remove_images/$', RemoveProfileImage.as_view(), name='remove-photo'),
    url(r'^devicetoken/$', DeviceToken.as_view(), name='device-token'),
    url(r'^notification_settings/$', NotificationSettings.as_view(), name='notification-settings'),
    url(r'^contact_support/$', ContactSupport.as_view(), name='contact-support'),
    url(r'^role_update/$', RoleUpdate.as_view(), name='update-role'),
    url(r'^update_notification_badge/$', UpdateNotificationBadge.as_view(), name='update-notification-badge-number'),
    url(r'^alert_fan/$', AlertFan.as_view(), name='alert fan when celebrity available'),
    url(r'^referral_request/$', ReferralRequest.as_view(), name='referral-request'),
    url(r'^referral_validate/$', ReferralValidate.as_view(), name='referral-validate'),
    url(r'^social_signup_validate/$', ValidateSocialSignup.as_view(), name='social-signup-validate'),
    url(r'^update_unseen_count/$', UpdateBookingCount.as_view(), name='update-unseen-count'),
    url(r'^signed_url/$', GetAWSSignedPostUrl.as_view(), name='signed-aws-post-url'),
    url(r'^get_signed_url/$', GetAWSSignedUrl.as_view(), name='signed-aws-get-url'),
    url(r'^group_account/$', GroupAccountsView.as_view(), name='group-account'),
    url(r'^group_types/$', GroupTypesView.as_view(), name='group-types'),
    url(r'^active_group_types/$', GroupTypesListing.as_view(), name='group-types-list'),
    url(r'^join_group/$', JoinGroupView.as_view(), name='join-group'),
    url(r'^social_links/$', SocialMediaUrls.as_view(), name='social-links'),
    url(r'^fan/group_follow/$', GroupAccountProfileFollow.as_view(), name='group-follow'),
    url(r'^celebrity_representative/?(?P<pk>[0-9a-zA-Z]{0,8})', CelebrityRepresentative.as_view(), name='celebrity-representative'),
    url(r'^validate_mobile/$', ValidateMobile.as_view(), name='validate-mobile'),
    url(r'^verify_mobile/$', VerifyMobile.as_view(), name='verify-mobile'),
    url(r'^twitter_login/$', TwitterLogin.as_view(), name='twitter-login'),
    url(r'^twitter_integration/$', TwitterIntegration.as_view(), name='twitter-integration'),
]

router = DefaultRouter()
router.register(r'user_details', UserDetails, base_name='user_details')
router.register(r'fan/celebrity_list', CelebrityList, base_name='celebrity_list')
router.register(r'fan/favourite_stars', FanFavouriteStars, base_name='Fan Favourite Stars')
router.register(r'referral_list', ReferralList, base_name='Referral List')
router.register(r'filtered_professions', FilterProfessions, base_name='filtered-profession')
router.register(r'group_list', GroupAccountList, base_name='group-account-list')
router.register(r'get_members/?(?P<pk>[0-9a-zA-Z]{0,8})', GetMembersList, base_name='members-list'),

urlpatterns = router.urls + urlpatterns
