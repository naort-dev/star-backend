from fcm_django.api.rest_framework import FCMDeviceAuthorizedViewSet


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
