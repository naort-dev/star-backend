# Generated by Django 2.1.5 on 2019-06-24 11:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0053_settingsnotifications_is_viewed'),
    ]

    operations = [
        migrations.AddField(
            model_name='celebrity',
            name='visibility',
            field=models.BooleanField(default=True, verbose_name='Visibility'),
        ),
        migrations.AddField(
            model_name='celebrity',
            name='website',
            field=models.CharField(blank=True, max_length=260, null=True, verbose_name='Website'),
        ),
        migrations.AlterField(
            model_name='recentactivity',
            name='activity_type',
            field=models.IntegerField(choices=[(1, 'comment'), (2, 'reaction'), (3, 'tip'), (4, 'rating'), (5, 'video')], default=1, verbose_name='Activity Type'),
        ),
    ]