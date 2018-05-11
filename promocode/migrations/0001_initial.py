# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-08-31 13:11
from __future__ import unicode_literals

from django.conf import settings
import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Promocode',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('code', models.CharField(max_length=100, verbose_name='Code')),
                ('valide_from', models.DateTimeField(verbose_name='Valide_from')),
                ('valide_to', models.DateTimeField(blank=True, verbose_name='Valide_to')),
                ('specific_user', models.BooleanField(default=False, verbose_name='Specified_users')),
                ('users_per_coupon', models.IntegerField(validators=[django.core.validators.MinValueValidator(1)], verbose_name='Users_per_coupon')),
                ('uses_per_coupon', models.IntegerField(validators=[django.core.validators.MinValueValidator(1)], verbose_name='Uses_per_coupon')),
                ('type', models.CharField(choices=[('fixed_amount', 'Fixed Amount'), ('percentage', 'Percentage')], default='fixed_amount', max_length=15)),
                ('discount', models.DecimalField(decimal_places=2, max_digits=9)),
                ('status', models.BooleanField(default=True, verbose_name='Promocode_status')),
                ('created_date', models.DateTimeField(auto_now_add=True, verbose_name='Created_date')),
                ('modified_date', models.DateTimeField(blank=True, editable=False, null=True, verbose_name='Modified_date')),
                ('promo_users', models.ManyToManyField(to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
