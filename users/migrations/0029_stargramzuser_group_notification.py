# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2019-01-21 08:31
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0028_auto_20190117_0930'),
    ]

    operations = [
        migrations.AddField(
            model_name='stargramzuser',
            name='group_notification',
            field=models.IntegerField(default=0, verbose_name='Group invite/support count'),
        ),
    ]
