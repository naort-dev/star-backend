# Generated by Django 2.1.5 on 2019-03-20 06:52

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0036_auto_20190314_0524'),
    ]

    operations = [
        migrations.AlterField(
            model_name='celebrity',
            name='user',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='celebrity_user', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='celebrityabuse',
            name='celebrity',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='celebrity_abuse', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='celebrityabuse',
            name='fan',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='fan_user_abuse', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='celebrityavailablealert',
            name='celebrity',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='alert_celebrity', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='celebrityavailablealert',
            name='fan',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='alert_fan', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='celebrityfollow',
            name='celebrity',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='celebrity_follow', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='celebrityfollow',
            name='fan',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='fan_user_follow', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='celebritygroupaccount',
            name='account',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='account_user', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='celebritygroupaccount',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='celebrity_account', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='celebrityprofession',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='celebrity_profession', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='celebrityview',
            name='celebrity',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='celebrity_view', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='celebrityview',
            name='fan',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='fan_user_view', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='devicetokens',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='device_user', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='groupaccount',
            name='user',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='group_account', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='notifications',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notification_user', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='profileimage',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='referral',
            name='referee',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='refer_referee', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='referral',
            name='referrer',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='refer_referrer', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='representative',
            name='celebrity',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='celebrity_representative', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='settingsnotifications',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='settings_user', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='socialmedialinks',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_social_links', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='userrolemapping',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stargramz_user', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='vanityurl',
            name='user',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='vanity_urls', to=settings.AUTH_USER_MODEL),
        ),
    ]
