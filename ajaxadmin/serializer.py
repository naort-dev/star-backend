from rest_framework import serializers
from stargramz.models import Stargramrequest, STATUS_TYPES
from utilities.konstants import OUTPUT_DATE_FORMAT


class RequestStatus(serializers.IntegerField):
    def to_representation(self, value):
        status_type = STATUS_TYPES.get_all_labels()
        return status_type[value]


class UserSerializer(serializers.RelatedField):
    def to_representation(self, value):
        return value.first_name + ' ' + value.last_name


class StargramzAjaxSerializer(serializers.ModelSerializer):
    celebrity = UserSerializer(read_only=True)
    fan = UserSerializer(read_only=True)
    request_status = RequestStatus(read_only=True)
    created_date = serializers.DateTimeField(format=OUTPUT_DATE_FORMAT, required=False)

    class Meta:
        model = Stargramrequest
        fields = ['id', 'fan', 'celebrity', 'occasion', 'request_status', 'created_date']
