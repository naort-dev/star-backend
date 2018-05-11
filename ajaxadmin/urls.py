from django.conf.urls import url, include
from .views import StargramzView, WidgetView, upload_images, delete_images, crop_images, avatar_image


urlpatterns = [
    url(r'^stargramzlist/$', StargramzView.as_view(), name='stargramzlist'),
    url(r'^usercount/$', WidgetView.as_view(), name='users-counts'),
    url(r'^upload/$', upload_images, name='upload-images'),
    url(r'^delete/$', delete_images, name='delete-images'),
    url(r'^crop/$', crop_images, name='crop-images'),
    url(r'^avatar/$', avatar_image, name='avatar-images'),
]
