import uuid
from django.db import models
from stargramz.models import Stargramrequest
from users.models import StargramzUser
from utilities.konstants import K, Konstants
# Create your models here.

TRANSACTION_STATUS = Konstants(
    K(pending=1, label='Pending'),
    K(authorized=2, label='Authorized'),
    K(captured=3, label='Captured'),
    K(cancelled=4, label='Cancelled'),
    K(refunded=5, label='Refunded'),
    K(failed=6, label='Failed'),
)


PAYOUT_STATUS = Konstants(
    K(pending=1, label='Pending'),
    K(transferred=2, label='Transferred'),
    K(reversed=3, label='Transfer Reversal'),
    K(payout_failed=4, label='Payout Failed'),
    K(check_pending=5, label='Check Pending'),
    K(check_transferred=6, label='Check Transferred')
)


class LogEvent(models.Model):
    event = models.TextField('Log event', max_length=1500, null=True, blank=True)
    type = models.CharField('Event Type', max_length=300, null=True, blank=True)
    card_type = models.CharField('Card Type', max_length=300, null=True, blank=True)
    status_message = models.CharField('Status Message', max_length=400, null=True, blank=True)
    created_date = models.DateTimeField('Created Date', auto_now_add=True)


class StarsonaTransaction(models.Model):
    starsona = models.ForeignKey(Stargramrequest, related_name='request_transaction', blank=False, null=False)
    fan = models.ForeignKey(StargramzUser, related_name='charge_fan_user')
    celebrity = models.ForeignKey(StargramzUser, related_name='charge_celebrity_user')
    amount = models.DecimalField('amount', max_digits=7, decimal_places=2, blank=False, null=False)
    created_date = models.DateTimeField('Created Date', auto_now_add=True)
    modified_date = models.DateTimeField('Modified Date', auto_now=True)
    transaction_status = models.IntegerField('Transaction Status', choices=TRANSACTION_STATUS.choices(),
                                             default=TRANSACTION_STATUS.pending, db_index=True)
    source_id = models.CharField(max_length=120, blank=False, null=False)
    stripe_transaction_id = models.CharField(max_length=120)
    stripe_refund_id = models.CharField(blank=True, null=True, max_length=120)
    comments = models.TextField('Comments', max_length=200, blank=True)

    class Meta:
        unique_together = (("starsona", "fan"), ("starsona", "celebrity"))

    def __str__(self):
        return 'Transaction %d' % self.pk

    def order_id(self):
        return 'OR-%s' % str(self.pk)


class StripeAccount(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    celebrity = models.ForeignKey(StargramzUser, related_name='stripe_celebrity_user')
    status = models.BooleanField('Status', default=False)
    response = models.TextField('Response', max_length=1500, blank=True)
    created_date = models.DateTimeField('Created Date', auto_now_add=True)


class PaymentPayout(models.Model):
    transaction = models.ForeignKey('StarsonaTransaction', related_name='transaction_payout')
    status = models.IntegerField('Transaction Status', choices=PAYOUT_STATUS.choices(),
                                 default=PAYOUT_STATUS.pending, db_index=True)
    celebrity = models.ForeignKey(StargramzUser, related_name='payout_celebrity')
    fan_charged = models.DecimalField('Fan Charged', max_digits=7, decimal_places=2)
    stripe_processing_fees = models.DecimalField('Stripe charges', max_digits=7, decimal_places=2)
    starsona_company_charges = models.DecimalField('Starsona company charges', max_digits=7, decimal_places=2)
    fund_payed_out = models.DecimalField('Fund Payed Out', max_digits=7, decimal_places=2)
    stripe_transaction_id = models.CharField('Transaction ID', max_length=30, blank=True)
    stripe_response = models.TextField('Stripe Response', max_length=1500, blank=True)
    created_date = models.DateTimeField('Created Date', auto_now_add=True)
    modified_date = models.DateTimeField('Modified Date', auto_now=True)
    comments = models.TextField('Comments', max_length=200, blank=True)
    referral_payout = models.BooleanField('Referral Payout', default=False)

    def __str__(self):
        return str(self.pk)
