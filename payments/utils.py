from payments.models import PAYMENT_TYPES


def in_app_price_reduction(record):
    in_app_price_percentage = 70
    if record.payment_type is PAYMENT_TYPES.in_app:
        return float(record.amount) * (in_app_price_percentage/100)
    else:
        return float(record.amount)
