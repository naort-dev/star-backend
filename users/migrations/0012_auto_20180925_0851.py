# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2018-09-25 08:51
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0011_auto_20180924_1244'),
    ]

    operations = [
        migrations.CreateModel(
            name='GroupType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('group_name', models.CharField(blank=True, max_length=260, null=True, verbose_name='Group name')),
                ('order', models.IntegerField(blank=True, null=True, verbose_name='list order')),
                ('created_date', models.DateTimeField(auto_now_add=True, verbose_name='Created date')),
                ('modified_date', models.DateTimeField(auto_now=True, verbose_name='Modified date')),
            ],
        ),
        migrations.AddField(
            model_name='celebritygroupaccount',
            name='celebrity_invite',
            field=models.BooleanField(default=False, verbose_name='Celebrity Invitation'),
        ),
        migrations.AddField(
            model_name='celebritygroupaccount',
            name='modified_date',
            field=models.DateTimeField(auto_now=True, verbose_name='Modified date'),
        ),
        migrations.AlterField(
            model_name='celebritygroupaccount',
            name='created_date',
            field=models.DateTimeField(auto_now_add=True, verbose_name='Created date'),
        ),
        migrations.AlterField(
            model_name='groupaccount',
            name='group_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='group_account_type', to='users.GroupType'),
        ),
    ]