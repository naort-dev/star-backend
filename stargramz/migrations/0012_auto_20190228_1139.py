# Generated by Django 2.1.5 on 2019-02-28 11:39

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('stargramz', '0011_auto_20190201_0703'),
    ]

    operations = [
        migrations.AlterField(
            model_name='comment',
            name='reply',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='reply_comment', to='stargramz.Comment'),
        ),
        migrations.AlterField(
            model_name='comment',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='commented_user', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='comment',
            name='video',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='comment_video', to='stargramz.StargramVideo'),
        ),
        migrations.AlterField(
            model_name='orderrelationship',
            name='occasion',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='through_occasion', to='stargramz.Occasion'),
        ),
        migrations.AlterField(
            model_name='orderrelationship',
            name='relation',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='through_relation', to='stargramz.OccasionRelationship'),
        ),
        migrations.AlterField(
            model_name='reaction',
            name='booking',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='booking_reaction', to='stargramz.Stargramrequest'),
        ),
        migrations.AlterField(
            model_name='reaction',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='user_reaction', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='reactionabuse',
            name='reaction',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='reaction_abuse', to='stargramz.Reaction'),
        ),
        migrations.AlterField(
            model_name='reactionabuse',
            name='reported_by',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='abuse_reported_user', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='reportabuse',
            name='reported_by',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='reported_user', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='reportabuse',
            name='request',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='request_abuse', to='stargramz.Stargramrequest'),
        ),
        migrations.AlterField(
            model_name='stargramrequest',
            name='celebrity',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='request_celebrity', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='stargramrequest',
            name='fan',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='request_fan', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='stargramrequest',
            name='occasion',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='request_occasion', to='stargramz.Occasion'),
        ),
        migrations.AlterField(
            model_name='stargramvideo',
            name='stragramz_request',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='request_video', to='stargramz.Stargramrequest'),
        ),
    ]
