from django.conf.urls import url, include

urlpatterns = [
    url(r'^user/', include('versioned.v2.users.urls')),
    url(r'^request/', include('versioned.v2.stargramz.urls')),
    url(r'^payments/', include('versioned.v2.payments.urls')),
]
