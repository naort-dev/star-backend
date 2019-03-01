from rest_framework.views import APIView
from utilities.mixins import ResponseViewMixin
from config.models import Config
from config.serializer import ConfigSerializer
import os
import json


class ConfigView(APIView, ResponseViewMixin):
    def get(self, request, *args, **kwargs):
        try:
            config = Config.objects.filter(status=True)
            serializer = ConfigSerializer(config, many=True)
            response_list = self.response_key_value_pair(serializer.data)
            file_type = os.environ.get("ENV")
            with open("config/in_app_pricing_%s.json" % file_type, mode="r") as file:
                in_app_pricing = file.read()
                data = json.loads(in_app_pricing)
                response_list.update(data)
            return self.jp_response(s_code='HTTP_200_OK', data={
                'config': response_list
            })
        except Exception as e:
            print(str(e))
            return self.jp_response(s_code='HTTP_200_OK', data={'config': {}})
