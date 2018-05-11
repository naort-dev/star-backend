# Register your models here.
from django.utils.translation import ugettext_lazy as _
from django.contrib import admin
from .models import LogEvent, StarsonaTransaction, StripeAccount, PaymentPayout


class TransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'starsona_id', 'fan', 'celebrity', 'transaction_status')

    fieldsets = (
        (_('Starsona Details'), {'fields': ('starsona', 'fan', 'celebrity')}),
        (_('Transaction Details'), {'fields': ('transaction_status', 'source_id',
                                               'stripe_transaction_id', 'stripe_refund_id', 'amount')}),
    )
    search_fields = ('id', 'fan__username', 'celebrity__username',)
    list_display_links = ('id',)
    list_filter = ('transaction_status',)
    readonly_fields = ('created_date', 'fan', 'celebrity', 'modified_date', 'source_id',
                       'stripe_transaction_id', 'stripe_refund_id')


class LogEventAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_date', 'type', 'status_message', 'card_type')

    fieldsets = (
        (_('Log Details'), {'fields': ('event', 'type', 'status_message', 'card_type')}),
    )
    search_fields = ('id',)
    readonly_fields = ('created_date',)


class LogStripeAccountAdmin(admin.ModelAdmin):
    list_display = ('id', 'celebrity', 'status',)

    fieldsets = (
        (_('Stripe'), {'fields': ('id', 'celebrity', 'status', 'response')}),
    )
    search_fields = ('id',)
    readonly_fields = ('created_date', 'id', 'celebrity', 'status')


class PayoutAdmin(admin.ModelAdmin):
    list_display = ('id', 'transaction_id', 'status', 'celebrity',)
    list_filter = ('status',)

    readonly_fields = ('celebrity', 'fan_charged', 'stripe_processing_fees', 'starsona_company_charges',
                       'fund_payed_out', 'stripe_response', 'stripe_transaction_id', 'created_date',
                       'modified_date')


admin.site.register(StarsonaTransaction, TransactionAdmin)
admin.site.register(LogEvent, LogEventAdmin)
admin.site.register(StripeAccount, LogStripeAccountAdmin)
admin.site.register(PaymentPayout, PayoutAdmin)
