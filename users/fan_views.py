from utilities.mixins import ResponseViewMixin
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from role.models import Role
from .models import StargramzUser, UserRoleMapping, FanRating, Celebrity, CelebrityFollow, CelebrityAbuse, Profession
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet
from .serializer import CelebrityRatingSerializer, UserSerializer, CelebrityFollowSerializer, \
    CelebrityAbuseSerializer, SuggestionSerializer
from decimal import Decimal
from math import ceil
from utilities.utils import ROLES
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


class ApproveFan(APIView, ResponseViewMixin):
    authentication_classes = (TokenAuthentication,)
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
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)
    pagination_class = CustomOffsetPagination
    serializer_class = UserSerializer

    def list(self, request):

        #role_id = Role.objects.get(code=ROLES.celebrity).id
        search_query = query_set = StargramzUser.objects.filter(celebrity_user__admin_approval=True) \
            .select_related('avatar_photo')\
            .prefetch_related('celebrity_user', 'images', 'celebrity_profession__profession')
        # if request.user:
        # search_query = query_set = query_set.exclude(username=request.user)
        sort = request.GET.get('sort')
        filter_by_name = request.GET.get('name')
        filter_by_lower_rate = request.GET.get('lrate')
        filter_by_upper_rate = request.GET.get('urate')
        filter_by_profession = request.GET.get('profession')
        exclude_celebrity = request.GET.get('exclude_celebrity')
        available = request.GET.get('available')
        if filter_by_name:
            query_set = search_name(filter_by_name, search_query)
        if filter_by_lower_rate and filter_by_upper_rate:
            try:
                query_set = query_set.filter(celebrity_user__rate__gte=filter_by_lower_rate)
                if float(filter_by_upper_rate) < 500:
                    query_set = query_set.filter(celebrity_user__rate__lte=filter_by_upper_rate)
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
                query_set = query_set.filter(celebrity_user__availability=True)

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


def search_name(filter_by_name, search_query):
    query_set_list = []
    query_field_dict = {}

    ######
    filter_by_name = filter_by_name.lower()
    filter_fields = [
        'first_name',
        'last_name',
        'nick_name',
        'celebrity_user__description',
        'celebrity_user__charity',
        'celebrity_profession__profession__title',
        'celebrity_profession__profession__parent__title'
    ]

    for term in filter_by_name.split():
        q_objects = Q()
        for key in filter_fields:
            kwargs_contains = {str('%s__icontains' % key): term}
            q_objects |= Q(**kwargs_contains)

        querying = search_query.filter(q_objects).distinct()
        if querying.exists():
            query_set_list.append(querying)
            query_set = first = query_set_list[0]
            for index in range(len(query_set_list) - 1):
                query_set = first | query_set_list[index + 1]
        else:
            query_set = querying

    ######
    # for term in filter_by_name.split():
    #     query_set = search_query
    #     list_filter_fields = ['first_name', 'last_name', 'nick_name', 'celebrity_user__description',
    #                           'celebrity_user__charity']
    #     profession_filters = ['celebrity_profession__profession__title',
    #                           'celebrity_profession__profession__parent__title']
    #     for list_field in list_filter_fields:
    #         kwargs = {list_field: None}
    #         query_field_dict[list_field] = list(set(query_set.values_list(list_field, flat=True).exclude(**kwargs)))
    #
    #     for key, value in query_field_dict.items():
    #         close_matches = get_close_matches(term.lower(), value)
    #         kwargs_list_in = {str('%s__in' % key): close_matches}
    #         kwargs_contains = {str('%s__icontains' % key): term}
    #         querying = query_set.filter(Q(**kwargs_list_in) | Q(**kwargs_contains))
    #         if querying.exists():
    #             query_set_list.append(querying)
    #     for profession_filter in profession_filters:
    #         kwargs = {str('%s__icontains' % profession_filter): term}
    #         querying = query_set.filter(**kwargs)
    #         if querying.exists():
    #             query_set_list.append(querying)
    #     if len(query_set_list) > 0:
    #         query_set = first = query_set_list[0]
    #         for postns in range(len(query_set_list) - 1):
    #             query_set = first = first | query_set_list[postns + 1]
    #     else:
    #         query_set = querying
    return query_set


class FanFavouriteStars(GenericViewSet, ResponseViewMixin):
    """
        The list of Favorite Stars
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)
    pagination_class = CustomOffsetPagination
    serializer_class = UserSerializer

    def list(self, request):
        user = StargramzUser.objects.get(username=request.user)
        search_query = query_set = StargramzUser.objects.filter(celebrity_follow__fan_id=user.id)
        filter_by_name = request.GET.get('name')
        if filter_by_name:
            query_set = search_name(filter_by_name, search_query)
        page = self.paginate_queryset(query_set.distinct())
        serializer = self.get_serializer(page, many=True)
        return self.paginator.get_paginated_response(serializer.data, key_name='celebrity_list')


# Remove this API after the next release Already handled the booking feedback in feedback API
class CelebrityRate(APIView, ResponseViewMixin):

    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)

    def post(self, request):
        """
            To save the rating of the celebrity
        """
        celebrity_id = request.data['celebrity']
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
            self.calculate(celebrity_user)
            data = CelebrityRatingSerializer(celebrity_fan_rating).data
            return self.jp_response('HTTP_200_OK', data={"fan_rating": data})
        else:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_LOGIN',
                                          self.error_msg_string(serializer.errors))

    def calculate(self, celebrity):
        """
            Calculate rating and save
        """
        total_user = FanRating.objects.filter(celebrity_id=celebrity.user_id)
        fan_count = Decimal(total_user.count())
        total_sum_rating = total_user.aggregate(Sum('fan_rate'))
        avg_rating = round(total_sum_rating['fan_rate__sum'] / fan_count, 1)
        round_off_avg = 0.5 * ceil(2.0 * float(avg_rating))
        celebrity.rating = round_off_avg
        celebrity.save()

        return round_off_avg


class CelebrityProfileFollow(APIView, ResponseViewMixin):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)

    def post(self, request):
        """
            To Follow a Celebrity by Fan
        """
        try:
            fan_user = StargramzUser.objects.get(username=request.user)
        except StargramzUser.DoesNotExist:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_SIGNUP', 'Invalid Signup User')
        try:
            celebrity_user = Celebrity.objects.get(user_id=request.data['celebrity'])
        except Celebrity.DoesNotExist:
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
            elif celebrity_exist:
                celebrity_exist.delete()
            stargramz_count = CelebrityFollow.objects.filter(celebrity_id=celebrity_user.user_id).count()
            celebrity_user.follow_count = stargramz_count
            celebrity_user.save()
            return self.jp_response(s_code='HTTP_200_OK',
                                    data={'follow_response': {'celebrity_user': request.data['celebrity'],
                                          'follow': follow, 'total_fans': stargramz_count}})
        else:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_CREATE',
                                          self.error_msg_string(serializer.errors))


class CelebrityFanAbuse(APIView, ResponseViewMixin):
    authentication_classes = (TokenAuthentication,)
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
                                    data={'celebrity_abuse_response': {'celebrity_user': celebirty_abuse.celebrity_id,
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

        query_set = StargramzUser.objects.filter(celebrity_user__admin_approval=True,
                                                 celebrity_user__rate__range=(min_rate, max_rate)
                                                 )\
            .select_related('avatar_photo')\
            .prefetch_related('images', 'celebrity_profession__profession')
        if available:
            query_set.filter(celebrity_user__availability=True)

        filter_by_name = request.GET.get('s')
        if filter_by_name:
            for term in filter_by_name.split():
                query_set = query_set.filter(Q(first_name__icontains=term) |
                                             Q(last_name__icontains=term) |
                                             Q(nick_name__icontains=term))
        # query_set = query_set[:10]
        data = SuggestionSerializer(query_set, many=True).data
        return self.jp_response('HTTP_200_OK', data={"suggestion_list": data})
