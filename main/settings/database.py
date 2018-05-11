import os

DEBUG = True
ALLOWED_HOSTS = ['https://stargramz.qburst.build', '127.0.0.1',]
ENV_DIR = ''
CLIENT_SITE_ADDR = 'https://stargramz.qburst.build:8000'


# Database
# https://docs.djangoproject.com/en/1.10/ref/settings/#databases
#
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'stargramzqb',
        'USER': 'ustargramzqb',
        'PASSWORD': '11uubts1',
        'HOST': 'localhost',
        'PORT': '',
    }
}
EMAIL_HOST_USER = 'obtbs123@gmail.com'
