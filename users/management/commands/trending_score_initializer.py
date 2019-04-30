from django.core.management.base import BaseCommand
from users.models import Celebrity, CelebrityFollow
from stargramz.models import Stargramrequest, STATUS_TYPES


class Command(BaseCommand):
    help = 'Initialize the trending score for all celebrities'

    def handle(self, *args, **kwargs):
        celebrities = Celebrity.objects.filter(admin_approval=True)
        for celebrity in celebrities:
            views = celebrity.view_count
            favorites = celebrity.follow_count
            purchase = Stargramrequest.objects.filter(celebrity=celebrity.user).exclude(request_status=STATUS_TYPES.draft).count()
            score = views + (5 * favorites) + (10 * purchase)
            celebrity.trending_star_score = score
            celebrity.save()
