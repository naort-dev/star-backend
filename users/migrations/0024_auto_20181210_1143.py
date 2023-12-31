# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2018-12-10 11:43
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0023_auto_20181207_1100'),
    ]

    operations = [
        migrations.AddField(
            model_name='settingsnotifications',
            name='email_notification',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='settingsnotifications',
            name='mobile_country_code',
            field=models.CharField(blank=True, max_length=5, null=True),
        ),
        migrations.AddField(
            model_name='settingsnotifications',
            name='mobile_notification',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='settingsnotifications',
            name='mobile_number',
            field=models.CharField(blank=True, max_length=15, null=True),
        ),
        migrations.AddField(
            model_name='settingsnotifications',
            name='secondary_email',
            field=models.EmailField(blank=True, max_length=254, null=True, unique=True),
        ),
        migrations.AlterField(
            model_name='notifications',
            name='notification_type',
            field=models.IntegerField(choices=[(1, 'Celebrity Starsona Request'), (2, 'Celebrity Starsona Message'), (3, 'Celebrity Account Updates'), (4, 'Fan Account Updates'), (5, 'Fan Starsona Messages'), (6, 'Fan Starsona Videos'), (7, 'Fan Email Starsona Videos'), (8, 'Email Notification'), (9, 'Secondary Email'), (10, 'Mobile Country Code'), (11, 'Mobile Number'), (12, 'Mobile Notification')], db_index=True, verbose_name='Notification Type'),
        ),
    ]
