# Generated by Django 2.1.5 on 2019-06-19 08:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0051_recentactivity'),
    ]

    operations = [
        migrations.AddField(
            model_name='recentactivity',
            name='public_visibility',
            field=models.BooleanField(default=True, verbose_name='Public Visibility'),
        ),
    ]
