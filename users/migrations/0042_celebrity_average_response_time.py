# Generated by Django 2.1.5 on 2019-04-26 09:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0041_merge_20190410_0718'),
    ]

    operations = [
        migrations.AddField(
            model_name='celebrity',
            name='average_response_time',
            field=models.DecimalField(blank=True, decimal_places=2, default=0.0, max_digits=7, verbose_name='Average Response Time'),
        ),
    ]
