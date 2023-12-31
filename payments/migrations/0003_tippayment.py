# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2018-09-12 05:19
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('stargramz', '0005_reaction'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('payments', '0002_auto_20180629_0714'),
    ]

    operations = [
        migrations.CreateModel(
            name='TipPayment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=7, verbose_name='amount')),
                ('created_date', models.DateTimeField(auto_now_add=True, verbose_name='Created Date')),
                ('modified_date', models.DateTimeField(auto_now=True, verbose_name='Modified Date')),
                ('transaction_status', models.IntegerField(choices=[(1, 'Pending'), (2, 'Tip credited'), (3, 'Tip payed out'), (4, 'Failed')], db_index=True, default=1, verbose_name='Transaction Status')),
                ('source_id', models.CharField(max_length=120)),
                ('stripe_transaction_id', models.CharField(max_length=120)),
                ('comments', models.TextField(blank=True, max_length=200, verbose_name='Comments')),
                ('booking', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tip_payment', to='stargramz.Stargramrequest')),
                ('celebrity', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tip_celebrity', to=settings.AUTH_USER_MODEL)),
                ('fan', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tip_fan', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
