# Generated by Django 2.1.5 on 2019-05-30 07:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0046_auto_20190528_1021'),
    ]

    operations = [
        migrations.AddField(
            model_name='stargramzuser',
            name='expiry_date',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Expiry Date'),
        ),
    ]