from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet
from utilities.permissions import CustomPermission
from utilities.mixins import ResponseViewMixin
from utilities.pagination import CustomOffsetPagination
from utilities.utils import ROLES, get_user_id, decode_pk
from users.models import StargramzUser, GroupAccount, GroupType, CelebrityGroupAccount, CelebrityFollow
from users.serializer import GroupListSerializer, GroupAccountSerializer, \
    GroupTypeSerializer, JoinGroupSerializer, GroupFollowSerializer, MemberListSerializer,\
    JoinGroupCelebritySerializer, GroupTypeListSerializer, CelebrityGroupAccountSerializer
from django.db.models import Q, When, F, Case
from .utils import search_name
from job.tasks import group_notify, invite_celebrity_notify


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
            user = None
            user = StargramzUser.objects.get(id=request.user.id)
        except Exception:
            pass
        try:
            group = GroupType.objects.all()
            serializer = GroupTypeListSerializer(group, many=True, context={"user": user})
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


class GroupTypesListing(APIView, ResponseViewMixin):

    def get(self, request):
        self.permission_classes = (CustomPermission,)
        try:
            groups = GroupAccount.objects.filter(admin_approval=True).values_list('group_type', flat=True).distinct()
            group_types_list = [group for group in groups]
            group_types_list = GroupType.objects.filter(id__in=group_types_list, active=True).order_by('order')
            serializer = GroupTypeSerializer(group_types_list, many=True)
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
            .prefetch_related('images', 'celebrity_profession__profession', 'group_account')

        group_type = request.GET.get('type')
        if group_type:
            search_query = search_query.filter(group_account__group_type=group_type)

        account = request.GET.get('account')
        member = request.GET.get('member')
        if account:
            user = get_user_id(account)
            filter_condition = {"celebrity_account__account": user, "celebrity_account__approved": True}
            if member:
                filter_condition.update({"celebrity_account__celebrity_invite": True})
            search_query = search_query.filter(**filter_condition)

        celebrity = request.GET.get('celebrity')
        if celebrity:
            user = get_user_id(celebrity)
            search_query = search_query.filter(account_user__user=user, account_user__approved=True)

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
            account = request.data.get('account', None)
            celebrity = request.data.get('celebrity', None)
            if account:
                request.data['user'] = user.id
                request.data['celebrity_invite'] = True
                validator = JoinGroupSerializer(data=request.data)
                if validator.is_valid():
                    group_details = validator.save()
                    serialized = CelebrityGroupAccountSerializer(group_details, many=True).data
                    group_details = [group.id for group in group_details]
                    group_notify.delay(group_details)
                    return self.jp_response(s_code='HTTP_200_OK', data=serialized)
                else:
                    return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_LOGIN', data=validator.errors)
            elif celebrity:
                request.data['account'] = user.id
                request.data['user'] = request.data.get('celebrity')
                request.data['approved'] = True
                validator = JoinGroupCelebritySerializer(data=request.data)
                if validator.is_valid():
                    group_details = validator.save()
                    serialized = CelebrityGroupAccountSerializer(group_details, many=True).data
                    group_details = [group.id for group in group_details]
                    invite_celebrity_notify.delay(group_details)
                    return self.jp_response(s_code='HTTP_200_OK', data=serialized)
                else:
                    return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_LOGIN', data=validator.errors)
        except Exception as e:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'EXCEPTION', 'Already requested.')


class GroupAccountProfileFollow(APIView, ResponseViewMixin):

    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)

    def post(self, request):
        """
            To Follow a group account by Fan
        """
        try:
            fan_user = StargramzUser.objects.get(username=request.user)
        except StargramzUser.DoesNotExist:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_SIGNUP', 'Invalid Signup User')

        serializer = GroupFollowSerializer(data=request.data)
        if serializer.is_valid():
            group_id = serializer.validated_data.get('group')

            try:
                group_exist = CelebrityFollow.objects.get(celebrity=group_id, fan_id=fan_user.id)
            except CelebrityFollow.DoesNotExist:
                group_exist = None

            follow = True if request.data['follow'] else False
            if follow:
                if not group_exist:
                    CelebrityFollow.objects.create(celebrity=group_id, fan_id=fan_user.id, is_group=True)
            elif group_exist:
                group_exist.delete()

            return self.jp_response(s_code='HTTP_200_OK', data={
                'group_follow_response': {'group_user': request.data['group'], 'follow': follow, }})
        else:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_CREATE', serializer.errors)


class GetMembersList(GenericViewSet, ResponseViewMixin):

    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)
    pagination_class = CustomOffsetPagination
    serializer_class = MemberListSerializer

    def list(self, request, pk):

        try:
            user_id = StargramzUser.objects.get(username=request.user).id
        except StargramzUser.DoesNotExist:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_SIGNUP', 'Invalid Signup User')

        search_query = StargramzUser.objects.select_related('avatar_photo', 'featured_photo') \
            .prefetch_related('images', 'celebrity_profession__profession', 'celebrity_account', 'vanity_urls')

        exclude_condition = {}
        option = request.GET.get('member', None)
        status = request.GET.get('status', None)
        celebrity = request.GET.get('celebrity', None)
        filter_by_name = request.GET.get('name', None)
        # the celebrity parameter is used for listing groups of a celebrity, authenticated user is celebrity
        # in the else part it will list the celebrity in a group, authenticated user is group
        if celebrity:
            filter_condition = {'group_account__admin_approval': True}
            # option will list the groups in which the celebrity is invited or supported or a member
            if option:
                filter_condition.update({'account_user__user_id': user_id})
                # the status = true will list the groups in which the celebrity is a member
                if status and status == 'true':
                    filter_condition.update(
                        {'account_user__approved': True, 'account_user__celebrity_invite': True}
                    )
            else:
                # here it will list the groups which is not the group of this celebrity there is no invitation nor
                # support
                exclude_condition.update({'account_user__user_id': user_id})

            result_query = search_query.exclude(**exclude_condition).filter(**filter_condition)
            # It will list the groups in which the celebrity is invited or the celebrity supports
            if status and status == 'false':
                filter_condition.update(
                    {'account_user__approved': True, 'account_user__celebrity_invite': True}
                )
                with_approved = search_query.exclude(**exclude_condition).filter(**filter_condition)
                result_query = result_query.difference(with_approved)
        else:
            filter_condition = {'celebrity_user__admin_approval': True}
            # option will list the admin_approved celebrities in which the celebrity is invited or supported or
            # a member of the group
            if option:
                filter_condition.update({'celebrity_account__account_id': user_id})
                # the status = true will list the members of the group
                if status and status == 'true':
                    filter_condition.update(
                        {'celebrity_account__approved': True, 'celebrity_account__celebrity_invite': True}
                    )
            else:
                # here it will list the non members of the group
                exclude_condition.update({'celebrity_account__account_id': user_id})

            result_query = search_query.exclude(**exclude_condition).filter(**filter_condition)
            # It will list the celebrities who are invited or supports the group but they are not the members of
            # the group
            if status and status == 'false':
                filter_condition.update(
                    {'celebrity_account__approved': True, 'celebrity_account__celebrity_invite': True}
                )
                with_approved = search_query.exclude(**exclude_condition).filter(**filter_condition)
                result_query = result_query.difference(with_approved)
        # it is not used features in Jan 15, 2019. it is created for search celebrity or group with the name
        if filter_by_name:
            filter_fields = [
                'first_name',
                'last_name',
                'nick_name'
            ]
            result_query = search_name(filter_by_name, result_query, filter_fields)
        if celebrity:
            result_query = result_query.order_by('first_name', 'nick_name', 'id')
        else:
            result_query = result_query.annotate(sort_name=Case(
                When(Q(show_nick_name=True) & Q(nick_name__isnull=False) & ~Q(nick_name=''), then=F('nick_name')),
                When(Q(show_nick_name=False), then=F('first_name')))).order_by('sort_name')
        page = self.paginate_queryset(result_query.distinct())
        serializer = self.get_serializer(page, many=True)

        return self.paginator.get_paginated_response(
            data={'group_user': serializer.data},
            key_name='group_follow_members'
        )

    def delete(self, request, pk):

        member_id = pk
        if member_id:
            try:
                member_id = decode_pk(member_id)
                account = CelebrityGroupAccount.objects.filter(id=member_id).filter(
                    Q(account=request.user) | Q(user=request.user)
                )
                account.delete()
            except Exception:
                return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_USER', 'Group member not found')
            return self.jp_response(s_code='HTTP_200_OK',
                                    data="successfully deleted")
        return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_USER', 'Group member id is wrong')
