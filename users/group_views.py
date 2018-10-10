from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet
from utilities.permissions import CustomPermission
from utilities.mixins import ResponseViewMixin
from utilities.pagination import CustomOffsetPagination
from utilities.utils import ROLES, get_user_id
from users.models import StargramzUser, GroupAccount, GroupType, CelebrityGroupAccount
from users.serializer import GroupListSerializer, GroupAccountSerializer, GroupAccountDataSerializer, \
    GroupTypeSerializer, JoinGroupSerializer


class GroupAccountsView(APIView, ResponseViewMixin):
    """
        Methods to add/update Group accounts and get the Group Types
    """
    def post(self, request):
        self.authentication_classes = (TokenAuthentication,)
        self.permission_classes = (IsAuthenticated, CustomPermission,)

        try:
            user = StargramzUser.objects.get(username=request.user, stargramz_user__role__code=ROLES.group_account)
        except Exception as e:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'EXCEPTION', data=str(e))

        group_account_fields = ['contact_first_name', 'contact_last_name', 'group_type', 'description', 'tags',
                                'website', 'phone', 'address', 'address_2', 'city', 'state', 'zip', 'country']

        request.data['user'] = user.id
        try:
            instance = GroupAccount.objects.get(user=user)
            serializer = GroupAccountSerializer(data=request.data, instance=instance, fields=group_account_fields)
        except GroupAccount.DoesNotExist:
            group_account_fields.append('user')
            serializer = GroupAccountSerializer(data=request.data, instance=None, fields=group_account_fields)

        if serializer.is_valid():
            serializer.save()
            return self.jp_response(s_code='HTTP_200_OK', data={'group_account': 'Created the account'})
        return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_LOGIN', data=serializer.errors)

    def get(self, request):
        self.permission_classes = (CustomPermission,)

        try:
            user = StargramzUser.objects.filter(group_account__admin_approval=True)
            serializer = GroupAccountDataSerializer(user, many=True)
            return self.jp_response(s_code='HTTP_200_OK', data={'group_accounts': serializer.data})
        except Exception as e:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'EXCEPTION', str(e))


class GroupTypesView(APIView, ResponseViewMixin):

    def get(self, request):
        self.permission_classes = (CustomPermission,)
        try:
            group_types = GroupType.objects.filter(active=True).order_by('order')
            serializer = GroupTypeSerializer(group_types, many=True)
            return self.jp_response(s_code='HTTP_200_OK', data={'group_types': serializer.data})
        except Exception as e:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'EXCEPTION', self.exception_response(str(e)))


class GroupAccountList(GenericViewSet, ResponseViewMixin):
    authentication_classes = ()
    permission_classes = (CustomPermission,)
    pagination_class = CustomOffsetPagination
    serializer_class = GroupListSerializer

    def list(self, request):
        search_query = StargramzUser.objects.all() \
            .select_related('avatar_photo') \
            .prefetch_related('images')

        group_type = request.GET.get('type')
        if group_type:
            search_query = search_query.filter(group_account__group_type=group_type)

        account = request.GET.get('account')
        if account:
            user = get_user_id(account)
            search_query = search_query.filter(celebrity_account__account=user)

        celebrity = request.GET.get('celebrity')
        if celebrity:
            user = get_user_id(celebrity)
            search_query = search_query.filter(account_user__user=user)

        if not celebrity and not account:
            search_query = search_query.filter(group_account__admin_approval=True)

        page = self.paginate_queryset(search_query.distinct())
        serializer = self.get_serializer(page, many=True)
        return self.paginator.get_paginated_response(serializer.data, key_name='group_list')


class JoinGroupView(APIView, ResponseViewMixin):

    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)

    def post(self, request):
        try:
            try:
                user = StargramzUser.objects.get(username=request.user)
            except Exception as e:
                return self.jp_error_response('HTTP_400_BAD_REQUEST', 'EXCEPTION', data=str(e))

            request.data['user'] = user.id
            request.data['celebrity_invite'] = True
            validator = JoinGroupSerializer(data=request.data)
            if validator.is_valid():
                validator.save()
                return self.jp_response(s_code='HTTP_200_OK', data="successfully joined the group")
            else:
                return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_LOGIN', data=validator.errors)
        except Exception as e:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'EXCEPTION', str(e))
