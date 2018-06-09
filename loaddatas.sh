#!/usr/bin/env bash

./manage.py createsuperuser
./manage.py loaddata config/fixtures/config.json
./manage.py loaddata role/fixtures/features.json
./manage.py loaddata role/fixtures/roles.json
./manage.py loaddata role/fixtures/role_feature_mapping.json
./manage.py loaddata stargramz/fixtures/relations.json
./manage.py loaddata stargramz/fixtures/occasions.json
./manage.py loaddata stargramz/fixtures/orderrelations.json
./manage.py loaddata users/fixtures/profession.json
