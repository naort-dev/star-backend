#!/usr/bin/env bash
set -e

if [[ -z "$SSL_SERVER_NAME" ]]; then
    echo "Must provide SSL_SERVER_NAME in environment" 1>&2
    exit 1
fi

if [[ -z "$SSL_SERVER_EMAIL" ]]; then
    echo "Must provide SSL_SERVER_EMAIL in environment" 1>&2
    exit 1
fi

sed -i -r "s/(^[ \t]*server_name[ \t]+).*(;.*)$/\1${SSL_SERVER_NAME}\2/g" /etc/nginx/sites-enabled/default

if [ ! -e /etc/letsencrypt/live/${SSL_SERVER_NAME}/cert.pem ]; then
   certbot --nginx -d ${SSL_SERVER_NAME} -n --agree-tos --email ${SSL_SERVER_EMAIL} --staging
fi

# crontab for auto renewal
exists=`crontab -l 2>/dev/null || true | grep "certbot" >/dev/null 2>&1 && echo 1 || echo 0`
if [[ "$exists" == 0 ]]; then
    echo "Installing certbot renew into crontab"
    line="0 0,12 * * * python -c 'import random; import time; time.sleep(random.random() * 3600)' && /usr/bin/certbot --staging renew"
    (crontab -l 2>/dev/null || true; echo "$line" ) | crontab -
fi

echo "Stopping existing nginx if needed"
/usr/sbin/nginx -s stop || true

echo "Starting main process:"
echo "    $@"
exec "$@"
