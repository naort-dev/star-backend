# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2019-01-08 09:17
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('notification', '0002_notification_user'),
    ]

    operations = [
        migrations.CreateModel(
            name='GroupAdminNotification',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('group_name', models.CharField(blank=True, max_length=150, null=True)),
                ('content', models.TextField(blank=True, max_length=300, null=True, verbose_name='contents')),
                ('created_date', models.DateTimeField(auto_now_add=True, verbose_name='Created Date')),
                ('modified_date', models.DateTimeField(auto_now=True, verbose_name='Modified Date')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='group_requested_user', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
