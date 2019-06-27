# Register your models here.
from django.utils.translation import ugettext_lazy as _
from django.contrib import admin
from .models import LogEvent, StarsonaTransaction, StripeAccount, PaymentPayout, TipPayment
from utilities.admin_utils import ReadOnlyModelAdmin


class TransactionAdmin(ReadOnlyModelAdmin):
    list_display = ('id', 'starsona_id', 'fan', 'celebrity', 'transaction_status')

    fieldsets = (
        (_('Starsona Details'), {'fields': ('starsona', 'fan', 'celebrity')}),
        (_('Transaction Details'), {'fields': ('transaction_status', 'source_id',
                                               'stripe_transaction_id', 'stripe_refund_id', 'amount', 'payment_type', 'actual_amount')}),
    )
    search_fields = ('id', 'fan__username', 'celebrity__username',)
    list_display_links = ('id',)
    list_filter = ('transaction_status',)
    readonly_fields = ('created_date', 'modified_date')


class LogEventAdmin(ReadOnlyModelAdmin):
    list_display = ('id', 'created_date', 'type', 'status_message', 'card_type')

    fieldsets = (
        (_('Log Details'), {'fields': ('event', 'type', 'status_message', 'card_type')}),
    )
    search_fields = ('id',)
    readonly_fields = ('created_date',)


class LogStripeAccountAdmin(ReadOnlyModelAdmin):
    list_display = ('id', 'celebrity', 'status',)

    fieldsets = (
        (_('Stripe'), {'fields': ('id', 'celebrity', 'status', 'response')}),
    )
    search_fields = ('id',)
    readonly_fields = ('created_date', 'id', 'celebrity', 'status')


class PayoutAdmin(ReadOnlyModelAdmin):
    list_display = ('id', 'transaction_id', 'status', 'celebrity',)
    list_filter = ('status',)

    readonly_fields = ('created_date', 'modified_date')


class TipPaymentAdmin(ReadOnlyModelAdmin):
    list_display = ('id', 'booking_id', 'fan', 'celebrity', 'transaction_status', 'created_date')

    fieldsets = (
        (_('Starsona Details'), {'fields': ('booking', 'fan', 'celebrity')}),
        (_('Transaction Details'),
         {'fields': ('transaction_status', 'source_id', 'stripe_transaction_id', 'amount', 'comments',
                     'tip_payed_out', 'payed_out_transaction_id', 'payed_out_response')}
        ),
    )
    search_fields = ('id', 'fan__username', 'celebrity__username',)
    list_display_links = ('id',)
    list_filter = ('transaction_status', 'created_date')
    readonly_fields = ('created_date', 'fan', 'celebrity', 'modified_date', 'source_id',
                       'stripe_transaction_id', 'booking', 'amount', 'comments', 'tip_payed_out',
                       'payed_out_transaction_id', 'payed_out_response')


admin.site.register(StarsonaTransaction, TransactionAdmin)
admin.site.register(LogEvent, LogEventAdmin)
admin.site.register(StripeAccount, LogStripeAccountAdmin)
admin.site.register(PaymentPayout, PayoutAdmin)
admin.site.register(TipPayment, TipPaymentAdmin)
