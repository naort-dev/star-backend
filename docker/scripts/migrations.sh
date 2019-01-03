#!/usr/bin/env bash
set -e

# python manage.py migrate --fake-initial
python manage.py makemigrations
python manage.py migrate
