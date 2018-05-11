from django.conf.urls import url, include
from news.views import NewsView


urlpatterns = [
    url(r'$^', NewsView.as_view(), name='news'),
]