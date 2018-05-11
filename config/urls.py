from django.conf.urls import url, include
from config.views import ConfigView


urlpatterns = [
    url(r'$^', ConfigView.as_view(), name='config'),
]
