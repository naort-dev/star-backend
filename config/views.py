from rest_framework.views import APIView
from utilities.mixins import ResponseViewMixin
from config.models import Config
from config.serializer import ConfigSerializer


class ConfigView(APIView, ResponseViewMixin):
    def get(self, request, *args, **kwargs):
        try:
            config = Config.objects.filter(status=True)
            serializer = ConfigSerializer(config, many=True)
            return self.jp_response(s_code='HTTP_200_OK', data={
                'config': self.response_key_value_pair(serializer.data)
            })
        except Exception as e:
            return self.jp_response(s_code='HTTP_200_OK', data={'config': {}})
