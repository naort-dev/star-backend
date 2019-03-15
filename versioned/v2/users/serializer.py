
from users.serializer import ProfessionSerializer, ProfessionFilterSerializer

class ProfessionSerializerV2(ProfessionSerializer):
    class Meta(ProfessionSerializer.Meta):
        fields = ('id', 'title', 'parent', 'description', 'child', 'file', 'order')


class ProfessionFilterSerializerV2(ProfessionFilterSerializer):
    class Meta(ProfessionFilterSerializer.Meta):
        fields = ('id', 'title', 'parent', 'description', 'child', 'file', 'order')
