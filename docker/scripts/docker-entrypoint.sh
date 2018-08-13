#!/usr/bin/env bash
set -e

if [[ -z "$ENV" ]]; then
    echo "Must provide ENV in environment" 1>&2
    exit 1
fi

cp .well-known/apple-app-site-association.$ENV .well-known/apple-app-site-association
cp templates/home/apps.html.$ENV templates/home/apps.html
cp config/fixtures/config.json.$ENV config/fixtures/config.json
cp utilities/constants.py.$ENV utilities/constants.py

if [ -n "$DATABASE_HOST" ]; then
while ! pg_isready --host=$DATABASE_HOST --dbname=$DATABASE_NAME --username==$DATABASE_USER
do
    echo "$(date) - waiting for database to start"
    sleep 5
done
fi

if [ -n "$QUEUE_HOST" ]; then
while ! (echo >/dev/tcp/$QUEUE_HOST/5672) &>/dev/null
do
    echo "$(date) - waiting for rabbitmq to start"
    sleep 5
done
fi

if [ -n "$BACKGROUND" ]; then
    eval "$BACKGROUND" &
fi

echo "Starting main process:"
echo "    $@"
exec "$@"
