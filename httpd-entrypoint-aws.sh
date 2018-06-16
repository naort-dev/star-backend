#!/usr/bin/env bash
set -e

sed -i -r "s/(^[ \t]+ProxyPass.*\/[ \t]+http:\/\/)[a-z].*(:[0-9]+\/.*$)/\1${PRIVATE_LB_HOSTNAME}\2/g" /etc/apache2/sites-enabled/000-default.conf

echo "Stopping existing apache if needed"
/usr/sbin/apachectl stop || true

echo "Starting main process:"
echo "    $@"
exec "$@"
