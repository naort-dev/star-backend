#!/usr/bin/env bash
set -e

# Following commands are not required for future deployments
# python manage.py migrate --fake payments 0007_auto_20190405_1126
# python manage.py migrate --fake payments 0008_auto_20190405_1151
# python manage.py migrate --fake users 0036_auto_20190405_1126

python manage.py migrate --fake-initial
