# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2018-11-20 12:00
from __future__ import unicode_literals

from django.db import migrations


def migration_update_user_emails_to_lowercase(apps, schema_editor):
    """
    Alter the users table to update username and email to lowercase
    :param apps:
    :param schema_editor:
    :return: Boolean
    """
    from django.db import connection
    cursor = connection.cursor()
    cursor.execute("UPDATE users_stargramzuser SET username = LOWER(username), email = LOWER(username);")
    return True


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0019_auto_20181105_1132'),
    ]

    operations = [
        migrations.RunPython(migration_update_user_emails_to_lowercase)
    ]
