#!/bin/bash

env:=dev

configure:

	git pull origin develop

ifndef env
	$(error env is undefined "make env=dev setup")
endif

	# Removing the files
	rm -rf .well-known/apple-app-site-association
	rm -rf templates/home/apps.html
	rm -rf config/fixtures/config.json
	rm -rf utilities/constants.py

	# Copying the file based on environment
	cp .well-known/apple-app-site-association.$(env) .well-known/apple-app-site-association
	cp templates/home/apps.html.$(env) templates/home/apps.html
	cp config/fixtures/config.json.$(env) config/fixtures/config.json
	cp utilities/constants.py.$(env) utilities/constants.py

restart-service:
# Restart the gunicorn service
ifeq ($(env), dev)
	sudo service stargramz.qburst.build-gunicorn restart
else
	sudo /etc/init.d/starsona-gunicorn restart
	# Update the config and professions model to rebuild the values in constants
endif


# Congigure Dev enviornment
setup: configure db-setup loaddatas restart-service 


# Load data from fixtures
# From Terminal "make loaddata"
# Uncomment the scripts for intial project setup
loaddatas:
	./manage.py loaddata config/fixtures/config.json
	# ./manage.py loaddata role/fixtures/features.json
	# ./manage.py loaddata role/fixtures/roles.json
	# ./manage.py loaddata role/fixtures/role_feature_mapping.json
	# ./manage.py loaddata stargramz/fixtures/relations.json
	./manage.py loaddata stargramz/fixtures/occasions.json
	./manage.py loaddata stargramz/fixtures/orderrelations.json
	# ./manage.py loaddata users/fixtures/profession.json

# Setup the project after running the migrations
# from Terminal "make setup"
db-setup:
	@echo 'Starting the Starsona setup process'
	pip install -U -r requirements.txt
	./manage.py makemigrations
	./manage.py migrate

# Stop all the worker and start again
tasks: kill-celery start-celery

kill-celery:
	pkill -f "main beat"& pkill -f "main worker"&

celery-status:
	ps ax  | grep 'celery' && echo $!

start-celery:
	celery -A main worker& celery -A main beat&

# Quickly seting up the deloying process
quick-setup:
	git pull origin develop
	sudo service stargramz.qburst.build-gunicorn restart

