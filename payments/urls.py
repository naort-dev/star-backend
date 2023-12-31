from django.conf.urls import url
from .views import GenerateEphemeralKey, CreateChargeFan, EventLog, AttachDetachSource, stripe_connect,\
    CreateAccount, EarningsList, StripeDashboard, CardsList, TipPayments, CreditCardNotification, InAppPurchase
from rest_framework.routers import DefaultRouter


urlpatterns = [
    url(r'^generatekey/$', GenerateEphemeralKey.as_view(), name='generate-customer-key'),
    url(r'^stripe_event/', EventLog.as_view(), name='stripe-event-log'),
    url(r'^createcharge/$', CreateChargeFan.as_view(), name='fan-charge-create'),
    url(r'^attach_detach_source/$', AttachDetachSource.as_view(), name='attach-detach-source-customer'),
    url(r'^oauth/connect/$', stripe_connect, name='oauth-connect'),
    url(r'^getstripeurl/$', CreateAccount.as_view(), name='get-stripe-url'),
    url(r'^stripe_dashboard/$', StripeDashboard.as_view(), name='stripe-dashboard'),
    url(r'^stripe_cards/$', CardsList.as_view(), name='stripe-cards'),
    url(r'^paytip/$', TipPayments.as_view(), name='pay-tip'),
    url(r'^card_notification/$', CreditCardNotification.as_view(), name='credit-card-notify'),
    url(r'^in_app_purchase/$', InAppPurchase.as_view(), name='ios-in-app-purchase')
]

router = DefaultRouter()
router.register(r'earnings_list', EarningsList, base_name='earnings-list')

urlpatterns = router.urls + urlpatterns
