from django.conf.urls import url
from .views import TipPaymentsV2

urlpatterns = [
    url(r'^paytip/$', TipPaymentsV2.as_view(), name='pay-tip-v2'),
    ]
