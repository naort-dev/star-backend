# Local development environment
## OSX

### Python

```
brew install pyenv
pyenv versions
pyenv local 3.6.7
export PATH="~/.pyenv/versions/3.6.7/bin:${PATH}"
python -m virtualenv ./venv-3.6.7
source ./venv-3.6.7/bin/activate
export PYCURL_SSL_LIBRARY=openssl
export LDFLAGS=-L/usr/local/opt/openssl/lib
export CPPFLAGS=-I/usr/local/opt/openssl/include
pip install -r requirements.txt
python -c 'import imageio; imageio.plugins.ffmpeg.download()'


```

For more convenient debugging of local gunicorn install gevent
```
pip install gevent

```

### Postgres
```
brew install postgresql@10
brew link --force postgresql@10
echo 'export PATH="/usr/local/opt/postgresql@10/bin:$PATH"' >> ~/.bash_profile
initdb /usr/local/var/postgres
pg_ctl -D /usr/local/var/postgres start
```

Create user and database
```
psql postgres
   create user postgres with encrypted password 'password';
   alter user postgres WITH createdb;
   create database starsona;
```

Restore database
```
psql starsona < staging_jan_30.sql
```

### RabbitMQ
```
brew install rabbitmq
rabbitmq-server

```

### Memcached
```
brew install memcached
memcached

```

### Elasticsearch
```
brew install elasticsearch
elasticsearch

```

### AWS config
Using staging credentials

~/.aws/credentials
```
[default]
aws_access_key_id=AKIAI6TVMDFSMUXZRWXQ
aws_secret_access_key=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
```

vi ~/.aws/config
```
[default]
region=us-east-1
role_arn=arn:aws:iam::376169159073:role/staging-backend-app-InstanceRole-4EVCXXJOJKG4
source_profile=default
```

### Tasks before first run ###

A static folder needs to be generated in project (as it's not under source control) by running:

```
python manage.py collectstatic
```

Some local files need to be renamed to their local names:

backend/templates/home.apps/html.dev
should be copied as
backend/templates/home/apps.html

backend/config/fixtures/config.json.dev
should be copied as
backend/config/fixtures/config.json


### Running Gunicorn under Intellij

Intellij preferences:
Debug Execution Deployment -> Python Debugger -> Gevent compatible (checked)

Script path:
<...>/backend/venv-3.6.7/bin/gunicorn

Parameters:
main.wsgi:application

Use specified interpreter: you should create a new SDK by going to File - Project Structure - SDKs and adding Python SDK Home Path: backend/venv-3.6.7/bin/python

Then choose this newly added SDK as the Specified Interpreter

Working directory:
<...>/backend/

Environment variables:
(copy/paste into the dialog)

```
PYTHONUNBUFFERED	1
AWS_STORAGE_BUCKET_NAME	starsona-stb-usea1
EMAIL_HOST	email-smtp.us-east-1.amazonaws.com
EMAIL_HOST_USER	AKIAJIHXXG4F6CM5LQAA
EMAIL_HOST_PASSWORD	AqV7b+nTqHNYODwE36FSHWbX+fhPTswGUZRmC6eQvSsj
EMAIL_PORT	587
EMAIL_USE_TLS	True
FCM_SERVER_KEY	AAAAXxcrrQc:APA91bEuZ2hTLIyzu244_I4_iHjiFuKCe1KpDjkLcM2SkAgpZCw-LHZOq_3UhdtctbZ-fuVEgxC7V-zMy3O8asB1eJAflkbTP6cwISCEzmro6E-UwIuSNTAQ6C-4W8Xj-IoPjw38grUH
STRIPE_WEB_HOOK	https://stargramz.qburst.build/api/v1/payments/oauth/connect
STRIPE_CLIENT_ID	ca_BNfbJXjIE3KOdWWcfEzFapDT2s8pjHNh
STRIPE_SECRET_KEY	sk_test_dISKeNgBVyio0OsLR1azrDyX
DATABASE_NAME	starsona
DATABASE_USER	postgres
DATABASE_PASSWORD	password
DATABASE_HOST	localhost
BRANCH_IO_KEY	key_test_jns5cyvoqDZSrm9kudg6Aikpxzmkoeqs
QUEUE_USER	guest
QUEUE_PASSWORD	guest
QUEUE_BACKEND	cache+memcached://localhost:11211/
QUEUE_HOST	localhost
QUEUE_BROKER_URL	amqp://guest:guest@localhost/
ADMIN_USERNAME	admin
ADMIN_PASSWORD	password
DEPLOYMENT_TYPE	swarm
GUNICORN_CMD_ARGS	--name=starsona --workers=1 --bind=0.0.0.0:9003 --worker-class=gevent --threads=1 --timeout=3600
DJANGO_SETTINGS_MODULE	main.settings.common
OBJC_DISABLE_INITIALIZE_FORK_SAFETY	YES
DEBUG	True
ELASTICSEARCH_ENDPOINT=http://localhost:9200/
```

### Running Migrations under Intellij

Script path:
<...>/backend/manage.py

Parameters:
migrate --fake-initial

Working directory:
<...>/backend/

Use specified interpreter:
same SDK as above

Environment variables:
same as Gunicorn

### Running Celery under Intellij

Script path:
<...>/backend/venv-3.6.7/bin/celery

Parameters
events:
-A main worker -n events

videos:
-A main worker -Q videos -n videos

Working directory:
<...>/backend/

Use specified interpreter:
same SDK as above

Environment variables:
same as Gunicorn
