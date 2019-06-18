from django.utils import timezone
import datetime

def high_cancel_check(query_set):
    count = query_set.filter(modified_date__gt=timezone.now() - datetime.timedelta(days=30)).count()
    if count > 3:
        return True, count
    else:
        return False, 0
