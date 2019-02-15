from django.contrib.auth.backends import ModelBackend
from users.models import StargramzUser


class PasswordlessAuthBackend(ModelBackend):
    """Log in to Django without providing a password.

    """
    def authenticate(self, request, username=None):
        try:
            return StargramzUser.objects.get(username=username)
        except StargramzUser.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return StargramzUser.objects.get(pk=user_id)
        except StargramzUser.DoesNotExist:
            return None
