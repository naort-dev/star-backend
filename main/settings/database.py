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
        'NAME': os.environ.get('DATABASE_NAME'),
        'USER': os.environ.get('DATABASE_USER'),
        'PASSWORD': os.environ.get('DATABASE_PASSWORD'),
        'HOST': os.getenv('DATABASE_HOST'),
        'PORT': '',
    }
}
