#!/usr/bin/env bash

./manage.py shell -c "import os; from django.contrib.auth import get_user_model;\
     User = get_user_model(); \
     User.objects.filter(username=os.environ.get('ADMIN_USERNAME'), is_superuser=True).delete(); \
     User.objects.create_superuser(os.environ.get('ADMIN_USERNAME'), os.environ.get('ADMIN_PASSWORD'))"
./manage.py loaddata config/fixtures/config.json
./manage.py loaddata role/fixtures/features.json
./manage.py loaddata role/fixtures/roles.json
./manage.py loaddata role/fixtures/role_feature_mapping.json
./manage.py loaddata stargramz/fixtures/relations.json
./manage.py loaddata stargramz/fixtures/occasions.json
./manage.py loaddata stargramz/fixtures/orderrelations.json
./manage.py loaddata users/fixtures/profession.json
