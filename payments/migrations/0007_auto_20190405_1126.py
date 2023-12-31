# Generated by Django 2.1.5 on 2019-04-05 11:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0006_auto_20190321_0514'),
    ]

    operations = [
        migrations.AddField(
            model_name='starsonatransaction',
            name='actual_amount',
            field=models.DecimalField(blank=True, decimal_places=2, default=0.0, max_digits=7, null=True, verbose_name='Actual amount'),
        ),
        migrations.AddField(
            model_name='starsonatransaction',
            name='ambassador_amount',
            field=models.DecimalField(blank=True, decimal_places=2, default=0.0, max_digits=7, null=True, verbose_name='Ambassador amount'),
        ),
    ]
