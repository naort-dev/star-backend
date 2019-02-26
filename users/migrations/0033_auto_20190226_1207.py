# Generated by Django 2.1.5 on 2019-02-26 12:07

from django.db import migrations
import json


def migrate_in_app_price(apps, schema_editor):

    celebrity = apps.get_model('users', 'Celebrity')
    with open("config/in_app_pricing_dev.json", mode="r") as file:
        data = file.read()
        data = json.loads(data)
        values = [data[i] for i in data]
    for star in celebrity.objects.all():
        try:
            if float(star.rate)-0.01 in values:
                star.in_app_price = float(star.rate)-0.01
            elif float(star.rate) > max(values):
                star.in_app_price = max(values)
            else:
                for value in values:
                    if value > float(star.rate):
                        star.in_app_price = value
                        break
            star.save()
        except Exception as e:
            print(str(e))


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0032_auto_20190225_1008'),
    ]

    operations = [
        migrations.RunPython(migrate_in_app_price)
    ]
