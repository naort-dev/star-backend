from django.db.models.query_utils import Q
from rest_framework.permissions import BasePermission
from users.models import USER_STATUS


class IsApprovedUser(BasePermission):
    """
    Allows access only to authenticated users.
    """
    def has_permission(self, request, view):
        return True if request.user.status == USER_STATUS.approved else False
