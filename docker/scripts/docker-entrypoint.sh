#!/usr/bin/env bash
set -e

if [[ -z "$ENV" ]]; then
    echo "Must provide ENV in environment" 1>&2
    exit 1
fi

#
# This is only for local Docker setup, when run in AWS ECS instance role set automatically
#
if [ -n "$AWS_INSTANCE_ROLE" ] \
    && [ -n "$AWS_ACCESS_KEY_ID" ] \
    && [ -n "$AWS_SECRET_ACCESS_KEY" ] \
    && [ -n "$AWS_DEFAULT_REGION" ]; then
echo "Creating local AWS credentials files..."
mkdir ~/.aws

cat <<EOF > ~/.aws/credentials
[default]
aws_access_key_id=$AWS_ACCESS_KEY_ID
aws_secret_access_key=$AWS_SECRET_ACCESS_KEY
EOF

cat <<EOF > ~/.aws/config
[default]
region=$AWS_DEFAULT_REGION
role_arn=$AWS_INSTANCE_ROLE
source_profile=default
EOF

unset AWS_ACCESS_KEY_ID
unset AWS_SECRET_ACCESS_KEY
unset AWS_DEFAULT_REGION

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
