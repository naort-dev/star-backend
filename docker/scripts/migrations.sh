#!/usr/bin/env bash
set -e

python manage.py migrate --fake-initial
