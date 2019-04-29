
def average_response_time_calculator(celebrity, created_date, modified_date):
    from users.models import Celebrity

    celebrity = Celebrity.objects.get(user_id=celebrity.id)
    time = celebrity.average_response_time
    response_time = (modified_date - created_date).days
    if time == 0:
        celebrity.average_response_time = response_time
    else:
        celebrity.average_response_time = round(((time + response_time) / 2), 2)
    celebrity.save()
