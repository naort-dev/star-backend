#!/usr/bin/env bash
set -e

python manage.py migrate --fake-initial
python manage.py set_es_indexing
