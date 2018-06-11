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

sed -i -r "s/(^\s*ServerName)(.*)$/\1 ${SSL_SERVER_NAME}/g" /etc/apache2/sites-enabled/000-default.conf

if [ ! -e /etc/letsencrypt/live/${SSL_SERVER_NAME}/cert.pem ]; then
   certbot --apache -d ${SSL_SERVER_NAME} -n --agree-tos --email ${SSL_SERVER_EMAIL}
fi

# crontab for auto renewal
line="0 0,12 * * * python -c 'import random; import time; time.sleep(random.random() * 3600)' && /usr/bin/certbot renew"
(crontab -l; echo "$line" ) | crontab -

echo "Starting main process:"
echo "    $@"
exec "$@"
