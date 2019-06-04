from utilities.mixins import ResponseViewMixin
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from role.models import Role
from .models import StargramzUser, UserRoleMapping, FanRating, Celebrity, CelebrityFollow, CelebrityAbuse, Profession
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet
from .serializer import CelebrityRatingSerializer, UserSerializer, CelebrityFollowSerializer, \
    CelebrityAbuseSerializer, SuggestionSerializer, CelebrityRatingSerializerEncoder
from utilities.utils import ROLES, decode_pk, encode_pk, average_rate_calculate
from utilities.pagination import CustomOffsetPagination
import ast
from django.db.models import Q, F, Value, Case, When, Sum
from utilities.permissions import CustomPermission
from rest_framework.decorators import list_route
from .constants import SORT
from difflib import get_close_matches
from django.db.models.functions import Concat
from config.models import Config
from config.constants import *
from .utils import search_name
from utilities.authentication import CustomAuthentication


class ApproveFan(APIView, ResponseViewMixin):
    authentication_classes = (CustomAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)

    def post(self, request):
        try:
            UserRoleMapping.objects.filter(user__username=request.user, role__code=ROLES.fan)\
                .update(is_complete=True)
            return self.jp_response('HTTP_200_OK', data={'fan': 'Successfully approved Fans.'})
        except UserRoleMapping.DoesNotExist:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_SIGNUP', 'Users Role doesnt match.')


class CelebrityList(GenericViewSet, ResponseViewMixin):
    """
        The list of celebrities and celebrity search
    """
    authentication_classes = (CustomAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)
    pagination_class = CustomOffsetPagination
    serializer_class = UserSerializer

    def __init__(self, *args, **kwargs):
        self.query_set = StargramzUser.objects.filter(
            (Q(celebrity_user__admin_approval=True) & Q(celebrity_user__star_approved=True)
             ) | Q(group_account__admin_approval=True)
        ).select_related('avatar_photo', 'featured_photo') \
            .prefetch_related('celebrity_user', 'celebrity_account', 'images', 'celebrity_profession__profession',
                              'group_account', 'vanity_urls', 'images')
        super().__init__(*args, **kwargs)

    def list(self, request):

        # role_id = Role.objects.get(code=ROLES.celebrity).id

        search_query = query_set = self.query_set
        # if request.user:
        # search_query = query_set = query_set.exclude(username=request.user)
        sort = request.GET.get('sort')
        filter_by_name = request.GET.get('name', None)
        filter_by_lower_rate = request.GET.get('lrate')
        filter_by_upper_rate = request.GET.get('urate')
        filter_by_profession = request.GET.get('profession')
        exclude_celebrity = request.GET.get('exclude_celebrity')
        available = request.GET.get('available')
        group_type = request.GET.get('group_type', None)
        if filter_by_name:
            filter_fields = [
                'first_name',
                'last_name',
                'nick_name',
                'celebrity_user__description',
                'celebrity_user__charity',
                'celebrity_profession__profession__title',
                'celebrity_profession__profession__parent__title'
            ]
            query_set = search_name(filter_by_name, search_query, filter_fields)
        if filter_by_lower_rate and filter_by_upper_rate:
            try:
                query_set = query_set.filter(
                    Q(celebrity_user__rate__gte=filter_by_lower_rate) | Q(group_account__admin_approval=True)
                )
                if float(filter_by_upper_rate) < 500:
                    query_set = query_set.filter(
                        Q(celebrity_user__rate__lte=filter_by_upper_rate) | Q(group_account__admin_approval=True)
                    )
            except Exception as e:
                return self.jp_error_response('HTTP_400_BAD_REQUEST', 'EXCEPTION', str(e))
        if filter_by_profession:
            try:
                filter_by_profession += ','
                x = ast.literal_eval(filter_by_profession)
            except Exception as e:
                return self.jp_error_response('HTTP_400_BAD_REQUEST', 'EXCEPTION', str(e))
            if type(x) is tuple:
                profession_ids = self.profession_ids(x)
                query_set = query_set.filter(celebrity_profession__profession_id__in=profession_ids)
            else:
                return self.jp_error_response('HTTP_400_BAD_REQUEST', 'EXCEPTION', 'Must be a list of values')
        if exclude_celebrity:
            try:
                exclude_celebrity = int(exclude_celebrity)
                query_set = query_set.exclude(id=exclude_celebrity)
            except Exception:
                return self.jp_error_response('HTTP_400_BAD_REQUEST', 'EXCEPTION', 'Must be an integer')
        if available:
            if available.lower() == 'true' or available == '1':
                # query_set = query_set.filter(celebrity_user__remaining_limit__gt=0)
                query_set = query_set.filter(
                    Q(celebrity_user__availability=True) | Q(group_account__admin_approval=True))

        if group_type:
            query_set = query_set.filter(group_account__admin_approval=True, group_account__group_type=group_type)
        elif not filter_by_name:
            query_set = query_set.exclude(group_account__admin_approval=True)

        if sort and sort in SORT:
            sort_list = [k for k in SORT[sort].split(',')]
            if sort is 'za' or 'az':
                query_set = query_set.annotate(search_name=Case(
                    When(Q(show_nick_name=True) & Q(nick_name__isnull=False) & ~Q(nick_name=''), then=F('nick_name')),
                    default=Concat('first_name', Value(' '), 'last_name'))).order_by(*sort_list)
            else:
                query_set = query_set.order_by(*sort_list)
        else:
            query_set = query_set.order_by('order', '-celebrity_user__view_count', 'celebrity_user__created_date')

        page = self.paginate_queryset(query_set.distinct())
        serializer = self.get_serializer(page, many=True)
        return self.paginator.get_paginated_response(serializer.data, key_name='celebrity_list')

    def profession_ids(self, filter_by_profession):
        professions = Profession.objects.filter(id__in=filter_by_profession)
        profession_ids = [profession.id for profession in professions]
        for profession in professions:
            if profession.parent_id is None:
                children = Profession.objects.filter(parent_id=profession.id)
                profession_ids += [child.id for child in children]
        return profession_ids

    @list_route(methods=['get'], permission_classes=[CustomPermission], authentication_classes=[],
                pagination_class=CustomOffsetPagination, serializer_class=UserSerializer)
    def get_list(self, request):
        request.user = None
        return self.list(request)


class FanFavouriteStars(GenericViewSet, ResponseViewMixin):
    """
        The list of Favorite Stars
    """
    authentication_classes = (CustomAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)
    pagination_class = CustomOffsetPagination
    serializer_class = UserSerializer

    def list(self, request):
        user = StargramzUser.objects.get(username=request.user)
        search_query = query_set = StargramzUser.objects.filter(
            celebrity_follow__fan_id=user.id,
            celebrity_follow__is_group=False
        )
        filter_by_name = request.GET.get('name')
        if filter_by_name:
            filter_fields = [
                'first_name',
                'last_name',
                'nick_name',
                'celebrity_user__description',
                'celebrity_user__charity',
                'celebrity_profession__profession__title',
                'celebrity_profession__profession__parent__title'
            ]
            query_set = search_name(filter_by_name, search_query, filter_fields)
        page = self.paginate_queryset(query_set.distinct())
        serializer = self.get_serializer(page, many=True)
        return self.paginator.get_paginated_response(serializer.data, key_name='celebrity_list')


# Remove this API after the next release Already handled the booking feedback in feedback API
class CelebrityRate(APIView, ResponseViewMixin):

    authentication_classes = (CustomAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)

    def post(self, request):
        """
            To save the rating of the celebrity
        """
        celebrity_id = request.data['celebrity']
        try:
            request.data['celebrity'] = celebrity_id = decode_pk(celebrity_id)
        except Exception:
            pass
        try:
            request.data["starsona"] = decode_pk(request.data["starsona"])
        except Exception:
            pass
        try:
            fan = StargramzUser.objects.get(username=request.user)
            request.data['fan'] = fan.id
        except StargramzUser.DoesNotExist:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_SIGNUP', 'Invalid Signup User')
        try:
            celebrity_user = Celebrity.objects.get(user_id=celebrity_id)
        except Celebrity.DoesNotExist:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'UNKNOWN_QUERY', 'Invalid Celebrity User')
        serializer = CelebrityRatingSerializer(data=request.data)
        if serializer.is_valid():
            fields = {
                'fan_rate': request.data['fan_rate'],
                'comments': request.data['comments'],
                'reason': serializer.validated_data.get('reason', ''),
            }
            celebrity_fan_rating, created = FanRating.objects.update_or_create(
                fan_id=fan.id, celebrity_id=celebrity_user.user_id, starsona_id=request.data['starsona'],
                defaults=fields)
            average_rate_calculate(celebrity_user)
            data = CelebrityRatingSerializerEncoder(celebrity_fan_rating).data
            return self.jp_response('HTTP_200_OK', data={"fan_rating": data})
        else:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_LOGIN',
                                          self.error_msg_string(serializer.errors))


class CelebrityProfileFollow(APIView, ResponseViewMixin):
    authentication_classes = (CustomAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)

    def post(self, request):
        """
            To Follow a Celebrity by Fan
        """
        from .authenticate_views import UserDetails
        try:
            fan_user = StargramzUser.objects.get(username=request.user)
        except StargramzUser.DoesNotExist:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_SIGNUP', 'Invalid Signup User')
        try:
            request.data['celebrity'] = UserDetails.verify_hash_token(UserDetails, request.data['celebrity'])
            celebrity = encode_pk(int(request.data['celebrity']))
            celebrity_user = Celebrity.objects.get(user_id=request.data['celebrity'])
        except Exception:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'UNKNOWN_QUERY', 'Invalid Celebrity User')
        try:
            celebrity_exist = CelebrityFollow.objects.get(celebrity_id=celebrity_user.user_id,
                                                          fan_id=fan_user.id)
        except CelebrityFollow.DoesNotExist:
            celebrity_exist = None
        serializer = CelebrityFollowSerializer(data=request.data)
        if serializer.is_valid():
            follow = True if request.data['follow'] else False
            if follow:
                if not celebrity_exist:
                    CelebrityFollow.objects.create(celebrity_id=celebrity_user.user_id, fan_id=fan_user.id)
                    celebrity_user.trending_star_score = F('trending_star_score') + 5
            elif celebrity_exist:
                celebrity_exist.delete()
            stargramz_count = CelebrityFollow.objects.filter(celebrity_id=celebrity_user.user_id).count()
            celebrity_user.follow_count = stargramz_count
            celebrity_user.save()
            return self.jp_response(s_code='HTTP_200_OK',
                                    data={'follow_response': {'celebrity_user': celebrity,
                                          'follow': follow, 'total_fans': stargramz_count}})
        else:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_CREATE',
                                          self.error_msg_string(serializer.errors))


class CelebrityFanAbuse(APIView, ResponseViewMixin):
    authentication_classes = (CustomAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)

    def post(self, request):
        """
            To Abuse a Celebrity by Fan
        """
        try:
            fan_user = StargramzUser.objects.get(username=request.user)
            request.data['fan'] = fan_user.id
        except StargramzUser.DoesNotExist:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_SIGNUP', 'Invalid Signup User')
        try:
            celebrity = request.data['celebrity']
            request.data['celebrity'] = decode_pk(request.data['celebrity'])
        except Exception:
            celebrity = encode_pk(request.data['celebrity'])
        try:
            celebrity_user = Celebrity.objects.get(user_id=request.data['celebrity'])
        except Celebrity.DoesNotExist:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'UNKNOWN_QUERY', 'Invalid Celebrity User')
        try:
            celebrity_exist = CelebrityAbuse.objects.get(celebrity_id=celebrity_user.user_id,
                                                         fan_id=fan_user.id)
        except CelebrityAbuse.DoesNotExist:
            celebrity_exist = None
        serializer = CelebrityAbuseSerializer(data=request.data, instance=celebrity_exist)
        if serializer.is_valid():
            celebirty_abuse = serializer.save()
            return self.jp_response(s_code='HTTP_200_OK',
                                    data={'celebrity_abuse_response': {'celebrity_user': celebrity,
                                                                       'abuse_comment': celebirty_abuse.abuse_comment}})
        else:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_CREATE',
                                          self.error_msg_string(serializer.errors))


class CelebritySuggestionList(APIView, ResponseViewMixin):
    authentication_classes = ()
    serializer_class = SuggestionSerializer

    def get(self, request):

        min_rate = request.GET.get('lrate') if request.GET.get('lrate') else MIN_RATE
        max_rate = request.GET.get('urate') if request.GET.get('urate') else MAX_RATE
        available = request.GET.get('available')
        if float(max_rate) >= 500:
            max_rate = 100000

        query_set = StargramzUser.objects.filter(
            (Q(celebrity_user__admin_approval=True) & Q(celebrity_user__admin_approval=True)
             & Q(celebrity_user__rate__range=(min_rate, max_rate)))
            | Q(group_account__admin_approval=True)
        )\
            .select_related('avatar_photo')\
            .prefetch_related('images', 'celebrity_profession__profession', 'group_account', 'vanity_urls')
        if available:
            query_set.filter(Q(celebrity_user__availability=True) | Q(group_account__admin_approval=True))

        filter_by_name = request.GET.get('s', None)
        if filter_by_name:
            for term in filter_by_name.split():
                query_set = query_set.filter(Q(first_name__icontains=term) |
                                             Q(last_name__icontains=term) |
                                             Q(nick_name__icontains=term))
        query_set = query_set[:50]
        data = SuggestionSerializer(query_set, many=True).data
        return self.jp_response('HTTP_200_OK', data={"suggestion_list": data})
