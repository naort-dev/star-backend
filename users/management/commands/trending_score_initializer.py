from django.core.management.base import BaseCommand
from users.tasks import trending_score_update


class Command(BaseCommand):
    help = 'Initialize the trending score for all celebrities'

    def handle(self, *args, **kwargs):
        trending_score_update()
