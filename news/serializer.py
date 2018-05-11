from rest_framework import serializers
from news.models import New
from utilities.constants import BASE_URL


class NewsSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    def get_image(self, obj):
        if obj.image:
            return "%smedia/%s" % (BASE_URL, obj.image)
        return None

    class Meta:
        model = New
        fields = ('id', 'title', 'description', 'image')