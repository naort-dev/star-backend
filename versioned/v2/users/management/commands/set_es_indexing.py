from django.core.management.base import BaseCommand
from versioned.v2.users.search import bulk_indexing


class Command(BaseCommand):
    help = 'Bulk index professions and celebrities in Elastic Search'

    def handle(self, *args, **kwargs):
        bulk_indexing()
