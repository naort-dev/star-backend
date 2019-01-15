# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2019-01-15 09:00
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stargramz', '0009_reactionabuse'),
    ]

    operations = [
        migrations.AddField(
            model_name='stargramvideo',
            name='fan_view_count',
            field=models.IntegerField(blank=True, default=0, null=True, verbose_name='Fan view count'),
        ),
        migrations.AddField(
            model_name='stargramvideo',
            name='public_view_count',
            field=models.IntegerField(blank=True, default=0, null=True, verbose_name='Public view count'),
        ),
    ]
