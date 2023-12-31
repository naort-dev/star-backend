# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2018-12-05 09:09
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0020_auto_20181120_1200'),
    ]

    operations = [
        migrations.CreateModel(
            name='Representative',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_name', models.CharField(max_length=128, verbose_name='First Name')),
                ('last_name', models.CharField(blank=True, max_length=128, null=True, verbose_name='Last Name')),
                ('email', models.EmailField(blank=True, db_index=True, max_length=254, null=True, unique=True, verbose_name='Email')),
                ('phone', models.CharField(blank=True, max_length=15, null=True, verbose_name='Phone Number')),
                ('email_notify', models.BooleanField(default=False, verbose_name='Email Notify')),
                ('sms_notify', models.BooleanField(default=False, verbose_name='SMS Notify')),
                ('created_date', models.DateTimeField(auto_now_add=True, verbose_name='Created date')),
                ('modified_date', models.DateTimeField(auto_now=True, verbose_name='Modified date')),
                ('celebrity', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='celebrity_representative', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
