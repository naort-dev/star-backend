from rest_framework.routers import DefaultRouter
from django.conf.urls import url
from .views import FCMViewset

router = DefaultRouter()

fcm_detail = FCMViewset.as_view({
    'put': 'update'
})

urlpatterns = [
    url(r'^devices/$', fcm_detail)
]
