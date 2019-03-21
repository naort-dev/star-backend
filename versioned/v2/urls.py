from django.conf.urls import url, include

urlpatterns = [
    url(r'^user/', include('versioned.v2.users.urls')),
]