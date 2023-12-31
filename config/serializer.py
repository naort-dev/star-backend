from rest_framework import serializers
from config.models import Config
import os
import json


class ConfigSerializer(serializers.ModelSerializer):
    value = serializers.SerializerMethodField()

    class Meta:
        model = Config
        fields = ('key', 'value',)

    def get_value(self, obj):
        environmental_variables = {
            'aws_bucket_name': 'AWS_STORAGE_BUCKET_NAME',
            'elastic_search_endpoint': 'ELASTICSEARCH_ENDPOINT'
        }
        json_data = ['decline_reasons', 'quick_comments', 'topics', 'cancel_booking_reasons']
        try:
            if obj.key in json_data:
                return json.loads(obj.value)
            elif obj.key in environmental_variables:
                return os.environ.get(environmental_variables[obj.key], None)
        except Exception as e:
            return obj.value
        return obj.value
