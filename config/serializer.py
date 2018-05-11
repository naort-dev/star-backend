from rest_framework import serializers
from config.models import Config
import json


class ConfigSerializer(serializers.ModelSerializer):
    value = serializers.SerializerMethodField()

    class Meta:
        model = Config
        fields = ('key', 'value',)

    def get_value(self, obj):
        try:
            if obj.key == 'decline_reasons':
                return json.loads(obj.value)
        except Exception as e:
            return obj.value
        return obj.value
