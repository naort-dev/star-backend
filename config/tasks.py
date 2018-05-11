from .models import Config
from main.celery import app
import json


@app.task(name='build_config_values')
def build_config():
    try:
        with open("config/constants.py", mode='w') as file:
            file.truncate()
            exclude_keys = ['decline_reasons']
            configs = Config.objects.all().order_by('id')
            for config in configs:
                if config.key not in exclude_keys:
                    file.write('%s = "%s"\n' % (config.key.upper(), config.value))
    except Exception as e:
        print(e)

    try:
        with open("config/versions.json", mode='w') as file:
            file.truncate()
            include_keys = ['android_version', 'ios_version']
            configs = Config.objects.all().order_by('id')
            versions = dict()
            for config in configs:
                if config.key in include_keys:
                    versions[config.key] = config.value
            json.dump(versions, file)

    except Exception as e:
        print(e)