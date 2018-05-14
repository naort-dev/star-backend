import os

DEBUG = True
ALLOWED_HOSTS = ['127.0.0.1',]
ENV_DIR = ''
CLIENT_SITE_ADDR = 'http://127.0.0.1:8000'


# Database
# https://docs.djangoproject.com/en/1.10/ref/settings/#databases
#
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'stargramz',
        'USER': 'postgres',
        'PASSWORD': 'root',
        'HOST': 'localhost',
        'PORT': '',
    }
}
EMAIL_HOST_USER = 'support@starsona.com'