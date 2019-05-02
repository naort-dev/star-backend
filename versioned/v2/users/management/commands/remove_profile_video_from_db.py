from django.core.management.base import BaseCommand
from config.models import Config
from users.models import Celebrity
from job.tasks import check_file_exist_in_s3

class Command(BaseCommand):
    help = 'This command will check whether the profile video exist in the s3 bucket, if not it will remove the video name from db'

    def handle(self, *args, **kwargs):
        config = Config.objects.get(key='authentication_videos').value
        celebrities = Celebrity.objects.all()
        for celebrity in celebrities:
            if celebrity.profile_video and not check_file_exist_in_s3(config + celebrity.profile_video):
                celebrity.profile_video = ""
                celebrity.save()
