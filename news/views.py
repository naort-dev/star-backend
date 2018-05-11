from rest_framework.views import APIView
from utilities.mixins import ResponseViewMixin
from news.models import New
from news.serializer import NewsSerializer


class NewsView(APIView, ResponseViewMixin):
    def get(self, request, *args, **kwargs):
        try:
            config = New.objects.all().order_by('-id')[:10]
            serializer = NewsSerializer(config, many=True)
            return self.jp_response(s_code='HTTP_200_OK', data={'news': serializer.data})
        except Exception as e:
            return self.jp_response(s_code='HTTP_200_OK', data={'config': {}})