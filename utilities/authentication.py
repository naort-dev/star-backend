from rest_framework.authentication import TokenAuthentication
import datetime, pytz

class CustomAuthentication(TokenAuthentication):
    def authenticate_credentials(self, *args, **kwargs):
        user, token = super().authenticate_credentials(*args, **kwargs)
        user.server_access_time_stamp = datetime.datetime.now(pytz.UTC)
        user.save()
        return user, token
