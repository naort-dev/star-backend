from django.core.management.base import BaseCommand
from users.models import StargramzUser, Celebrity
from stargramz.models import Stargramrequest, STATUS_TYPES
"""
 Status : The data from the production gives irregular data,
 difference between video record and booking record returns more than 7 days.
"""

class Command(BaseCommand):

    def handle(self, *args, **kwargs):
        celebrities = StargramzUser.objects.filter(celebrity_user__admin_approval=True)
        for celebrity in celebrities:
            requests = Stargramrequest.objects.filter(request_status=STATUS_TYPES.completed, celebrity_id=celebrity.id)
            dates = []
            for request in requests:
                a = request.created_date
                b = request.modified_date
                c = b-a
                dates.append(c.days)
            if len(dates) > 0:
                if sum(dates) > 0:
                    average = sum(dates)/len(dates)
                else:
                    average = 1
            else:
                average = 0
            star = Celebrity.objects.get(user_id=celebrity.id)
            star.average_response_time = round(average, 2)
            star.save()
