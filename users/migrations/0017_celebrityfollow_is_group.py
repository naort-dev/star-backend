# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2018-10-11 10:41
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0016_auto_20181010_1114'),
    ]

    operations = [
        migrations.AddField(
            model_name='celebrityfollow',
            name='is_group',
            field=models.BooleanField(default=False, verbose_name='Is Group account'),
        ),
    ]