from django.contrib import admin
from .models import VideoFavorites
from utilities.admin_utils import ReadOnlyModelAdmin

class VideoFavoritesAdmin(ReadOnlyModelAdmin):
    model = VideoFavorites
    list_display = ('id', 'celebrity', 'booking', 'video', 'created_date')
    search_fields = ('celebrity__email', 'celebrity__first_name', 'celebrity__last_name', 'celebrity__nick_name')


admin.site.register(VideoFavorites, VideoFavoritesAdmin)
