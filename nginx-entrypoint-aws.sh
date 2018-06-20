#!/usr/bin/env bash
set -e

if [[ -z "$PRIVATE_LB_HOSTNAME" ]]; then
    echo "Must provide PRIVATE_LB_HOSTNAME in environment" 1>&2
    exit 1
fi

sed -i -r "s/(^[ \t]+proxy_pass[ \t]+http:\/\/).*(:[0-9]+.*$)/\1${PRIVATE_LB_HOSTNAME}\2/g" /etc/nginx/sites-enabled/default

echo "Starting main process:"
echo "    $@"
exec "$@"
