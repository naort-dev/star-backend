# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2018-05-09 11:21
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Config',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(max_length=100, unique=True, verbose_name='Key')),
                ('value', models.CharField(blank=True, max_length=350, verbose_name='Value')),
                ('status', models.BooleanField(default=True, verbose_name='Status')),
                ('created_date', models.DateTimeField(auto_now_add=True, verbose_name='Created Date')),
                ('modified_date', models.DateTimeField(auto_now=True, verbose_name='Modified Date')),
            ],
            options={
                'ordering': ['id'],
            },
        ),
    ]
