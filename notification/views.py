from fcm_django.api.rest_framework import FCMDeviceAuthorizedViewSet
from .serializer import GroupAdminNotificationSerializer
from rest_framework.views import APIView
from utilities.mixins import ResponseViewMixin
from users.models import StargramzUser
from job.tasks import send_admin_mail
import json
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated


class FCMViewset(FCMDeviceAuthorizedViewSet):

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        try:
            obj = queryset.get(registration_id=self.request.data['registration_id'])
        except Exception:
            obj = None
        if obj:
            self.check_object_permissions(self.request, obj)
        return obj


class MailAdmin(APIView, ResponseViewMixin):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        data = request.data.get("body", None)
        try:
            user = StargramzUser.objects.get(username=request.user)
        except Exception as e:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_USER', "Invalid user")
        data.update({"user": user.id, "content": json.dumps(data)})
        serializer = GroupAdminNotificationSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            data.update(
                {
                    "user_name": user.get_short_name(),
                    "group_type": data.get("group_type", '').capitalize(),
                    "group_name": data.get("group_name", '').capitalize()
                }
            )
            subject = "New Group Request"
            template = "admin_notification"
            send_admin_mail.delay(subject, template, data)
            return self.jp_response('HTTP_200_OK', data={'message': "Your request to add the group has been sent."})
        else:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'EXCEPTION', 'Data Invalid')
