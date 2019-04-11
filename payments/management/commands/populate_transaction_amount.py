from django.core.management.base import BaseCommand
from django.db import transaction
from payments.models import StarsonaTransaction, PAYMENT_TYPES
from job.tasks import verify_referee_discount


class Command(BaseCommand):
    help = 'Update actual amount field with calculated amount in StarsonaTransaction table'

    def handle(self, *args, **kwargs):
        transactions = StarsonaTransaction.objects.all()
        try:
            with transaction.atomic():
                for star_transaction in transactions:
                    if star_transaction.amount:
                        if star_transaction.payment_type is PAYMENT_TYPES.in_app:
                            amount = round((float(star_transaction.amount) * (70.0 / 100.0)), 2)
                        else:
                            amount = float(star_transaction.amount)
                        referee_discount = verify_referee_discount(star_transaction.celebrity_id)
                        star_transaction.actual_amount = round((float(amount) * (referee_discount / 100.0)), 2)
                    else:
                        star_transaction.actual_amount = 0.0
                    star_transaction.save()
        except Exception as e:
            pass
