#!/usr/bin/env bash
set -e

if [[ -z "$ADMIN_USERNAME" ]]; then
    echo "Must provide ADMIN_USERNAME in environment" 1>&2
    exit 1
fi

if [[ -z "$ADMIN_PASSWORD" ]]; then
    echo "Must provide ADMIN_PASSWORD in environment" 1>&2
    exit 1
fi

echo 'Creating superuser...'
python manage.py shell -c "import os; from django.contrib.auth import get_user_model;\
     User = get_user_model(); \
     User.objects.filter(username=os.environ.get('ADMIN_USERNAME'), is_superuser=True).delete(); \
     User.objects.create_superuser(os.environ.get('ADMIN_USERNAME'), os.environ.get('ADMIN_PASSWORD'))"

echo 'Loading data...'
python manage.py loaddata config/fixtures/config.json
python manage.py loaddata role/fixtures/features.json
python manage.py loaddata role/fixtures/roles.json
python manage.py loaddata role/fixtures/role_feature_mapping.json
python manage.py loaddata stargramz/fixtures/relations.json
python manage.py loaddata stargramz/fixtures/occasions.json
python manage.py loaddata stargramz/fixtures/orderrelations.json
python manage.py loaddata users/fixtures/profession.json

echo 'All done'