from payments.models import PAYMENT_TYPES
from users.models import StargramzUser

def in_app_price_reduction(record):
    in_app_price_percentage = 70
    if record.payment_type is PAYMENT_TYPES.in_app:
        return float(record.amount) * (in_app_price_percentage/100)
    else:
        return float(record.amount)

def has_ambassador(celebrity_id):
    try:
        celebrity = StargramzUser.objects.get(id=celebrity_id)
        if celebrity.ambassador:
            if celebrity.ambassador.is_ambassador:
                return True
        return False
    except Exception:
        return False
