from rest_framework import serializers
from .models import StarsonaTransaction
from stargramz.serializer import TransactionStargramzSerializer


class EphemeralKeySerializer(serializers.Serializer):

    api_key = serializers.CharField()


class ChargeSerializer(serializers.ModelSerializer):
    source = serializers.CharField(required=True, allow_blank=False, allow_null=False)

    class Meta:
        model = StarsonaTransaction
        fields = ('starsona', 'fan', 'amount', 'source')


class AttachDetachSourceSerializer(serializers.Serializer):
    customer = serializers.CharField(required=True, allow_blank=False, allow_null=False)
    source = serializers.CharField(required=True, allow_blank=False, allow_null=False)
    action = serializers.BooleanField(required=True)


class StarsonaTransactionSerializer(serializers.ModelSerializer):
    starsona = TransactionStargramzSerializer(read_only=True)
    amount = serializers.DecimalField(read_only=True, max_digits=7, decimal_places=2)
    id = serializers.CharField(read_only=True, source='order_id')

    class Meta:
        model = StarsonaTransaction
        fields = ('id', 'starsona', 'created_date', 'amount')
