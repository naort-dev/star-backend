# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2018-10-03 10:26
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0013_grouptype_active'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='celebritygroupaccount',
            unique_together=set([('user', 'account')]),
        ),
    ]
