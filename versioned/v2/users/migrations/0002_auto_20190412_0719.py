# Generated by Django 2.1.5 on 2019-04-12 07:19

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0041_merge_20190410_0718'),
        ('users2', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CelebrityDisplayOrganizer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(blank=True, max_length=120, null=True)),
                ('profession', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='profession_celebrity', to='users.Profession')),
            ],
        ),
        migrations.AddField(
            model_name='celebritydisplay',
            name='order',
            field=models.IntegerField(blank=True, null=True, verbose_name='celebrity order'),
        ),
        migrations.AlterField(
            model_name='celebritydisplay',
            name='celebrity',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='celebrity_display', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='celebritydisplay',
            name='celebrity_display',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='celebrity_display_organizer', to='users2.CelebrityDisplayOrganizer'),
        ),
    ]
