# Generated by Django 2.1.5 on 2019-02-28 11:39

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('notification', '0003_groupadminnotification'),
    ]

    operations = [
        migrations.AlterField(
            model_name='groupadminnotification',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='group_requested_user', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='notification',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='notifcation_user', to=settings.AUTH_USER_MODEL),
        ),
    ]