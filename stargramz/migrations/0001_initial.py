# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2018-06-29 07:14
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Occasion',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=256, verbose_name='Title')),
                ('occasion_image', models.FileField(blank=True, null=True, upload_to='')),
                ('date_required', models.BooleanField(default=False, verbose_name='Date mandatory')),
                ('type', models.IntegerField(choices=[(0, 'Type 0'), (1, 'Type 1'), (2, 'Type 2'), (3, 'Type 3'), (4, 'Type 4'), (5, 'Type 5'), (6, 'Type 6'), (7, 'Type 7'), (8, 'Type 8')], default=1)),
                ('other_check', models.BooleanField(default=False, verbose_name='Other check')),
                ('request_type', models.IntegerField(choices=[(1, 'Personalized video shout-out'), (2, 'Event Announcement'), (3, 'Live Question and Answer')], default=1)),
                ('created_date', models.DateTimeField(auto_now_add=True, verbose_name='Created date')),
                ('visibility', models.BooleanField(default=True, verbose_name='Public Visibility')),
            ],
        ),
        migrations.CreateModel(
            name='OccasionRelationship',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=256, verbose_name='Title')),
                ('status', models.BooleanField(default=False, verbose_name='Status')),
            ],
            options={
                'ordering': ('through_relation__order', 'title'),
            },
        ),
        migrations.CreateModel(
            name='OrderRelationship',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order', models.IntegerField(default=0)),
            ],
            options={
                'ordering': ('order',),
            },
        ),
        migrations.CreateModel(
            name='ReportAbuse',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('comments', models.TextField(verbose_name='Comments')),
                ('read_flag', models.BooleanField(default=False, verbose_name='Verified abuse')),
                ('created_date', models.DateTimeField(auto_now_add=True, verbose_name='Created Date')),
            ],
        ),
        migrations.CreateModel(
            name='Stargramrequest',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('booking_title', models.CharField(blank=True, max_length=255, null=True, verbose_name='Booking title')),
                ('request_details', models.TextField()),
                ('share_check', models.BooleanField(default=False)),
                ('due_date', models.DateField(auto_now_add=True)),
                ('request_status', models.IntegerField(choices=[(0, 'Draft'), (1, 'Payment Approved'), (2, 'Pending'), (3, 'Processing'), (4, 'Video Approval'), (5, 'Cancelled'), (6, 'Completed')], default=0)),
                ('public_request', models.BooleanField(default=False)),
                ('priorty', models.BooleanField(default=False)),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('modified_date', models.DateTimeField(auto_now=True)),
                ('from_audio_file', models.CharField(blank=True, max_length=260, null=True)),
                ('to_audio_file', models.CharField(blank=True, max_length=260, null=True)),
                ('comment', models.CharField(blank=True, max_length=260, null=True)),
                ('request_type', models.IntegerField(choices=[(1, 'Personalized video shout-out'), (2, 'Event Announcement'), (3, 'Live Question and Answer')], default=1)),
            ],
            options={
                'verbose_name_plural': 'Bookings',
                'verbose_name': 'Bookings',
            },
        ),
        migrations.CreateModel(
            name='StargramVideo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('video', models.CharField(blank=True, max_length=600, null=True, verbose_name='Request Video')),
                ('thumbnail', models.CharField(blank=True, max_length=600, null=True, verbose_name='Thumbnail Image')),
                ('duration', models.TimeField(blank=True, null=True, verbose_name='Duration')),
                ('read_status', models.BooleanField(default=False)),
                ('status', models.IntegerField(choices=[(1, 'Completed'), (2, 'Approved'), (3, 'Rejected'), (4, 'Live Question'), (5, 'Live Answer')], default=1)),
                ('featured', models.BooleanField(default=False)),
                ('created_date', models.DateTimeField(auto_now_add=True, verbose_name='Created Date')),
                ('modified_date', models.DateTimeField(auto_now=True, verbose_name='Modified Date')),
                ('visibility', models.BooleanField(default=True, verbose_name='Public Visibility')),
                ('width', models.IntegerField(blank=True, null=True, verbose_name='Width')),
                ('height', models.IntegerField(blank=True, null=True, verbose_name='Height')),
                ('stragramz_request', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='request_video', to='stargramz.Stargramrequest')),
            ],
            options={
                'ordering': ['-id', '-created_date'],
                'verbose_name_plural': 'Video',
                'verbose_name': 'Videos',
            },
        ),
    ]
