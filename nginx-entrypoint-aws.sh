#!/usr/bin/env bash
set -e

sed -i -r "s/(^[ \t]+proxy_pass[ \t]+http:\/\/).*(:[0-9]+.*$)/\1${PRIVATE_LB_HOSTNAME}\2/g" /etc/nginx/sites-enabled/default

echo "Starting main process:"
echo "    $@"
exec "$@"
