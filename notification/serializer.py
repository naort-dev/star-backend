from rest_framework import serializers
from notification.models import GroupAdminNotification


class GroupAdminNotificationSerializer(serializers.ModelSerializer):

    class Meta:
        model = GroupAdminNotification
        fields = ('user', 'group_name', 'content')
