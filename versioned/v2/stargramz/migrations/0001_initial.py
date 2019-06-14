# Generated by Django 2.1.5 on 2019-06-13 10:31

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('stargramz', '0016_stargramrequest_booking_statement'),
    ]

    operations = [
        migrations.CreateModel(
            name='VideoFavorites',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_date', models.DateTimeField(auto_now_add=True, verbose_name='Created Date')),
                ('booking', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='favorite_booking', to='stargramz.Stargramrequest')),
                ('celebrity', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='celebrity_video_favorites', to=settings.AUTH_USER_MODEL)),
                ('video', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='favorite_video', to='stargramz.StargramVideo')),
            ],
        ),
    ]
