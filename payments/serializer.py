from rest_framework import serializers
from .models import StarsonaTransaction, TipPayment, PaymentPayout, PAYOUT_STATUS
from stargramz.serializer import TransactionStargramzSerializer
from hashids import Hashids
hashids = Hashids(min_length=8)


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
    payout_status = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = StarsonaTransaction
        fields = ('id', 'starsona', 'created_date', 'amount', 'payout_status')

    def get_payout_status(self, obj):
        try:
            return PAYOUT_STATUS.get_label(PaymentPayout.objects.values_list('status', flat=True).get(
                transaction_id=obj.id,
                celebrity_id=obj.celebrity_id
            ))
        except Exception:
            return PAYOUT_STATUS.get_label(1)


class BookingValidate(serializers.ModelSerializer):
    class Meta:
        model = TipPayment
        fields = ('booking',)


class TipPaymentSerializer(serializers.ModelSerializer):
    source = serializers.CharField(required=True, allow_blank=False, allow_null=False)
    amount = serializers.DecimalField(required=True, max_digits=7, decimal_places=2)

    class Meta:
        model = TipPayment
        fields = ('booking', 'amount', 'source', 'celebrity', 'fan')


class CreditCardNotificationSerializer(serializers.Serializer):
    attach = serializers.BooleanField(required=True)
