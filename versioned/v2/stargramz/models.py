from django.db import models

class VideoFavorites(models.Model):
    booking = models.ForeignKey('stargramz.Stargramrequest', related_name='favorite_booking', on_delete=models.CASCADE)
    video = models.ForeignKey('stargramz.StargramVideo', related_name='favorite_video', on_delete=models.CASCADE)
    celebrity = models.ForeignKey('users.StargramzUser', related_name='celebrity_video_favorites', on_delete=models.CASCADE)
    created_date = models.DateTimeField('Created Date', auto_now_add=True)

    class Meta:
        verbose_name = 'Video Like'
