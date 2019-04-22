from users.authenticate_views import FilterProfessions, Professions, UserRegister
from .serializer import ProfessionFilterSerializerV2, ProfessionSerializerV2, SearchSerializer,\
    CelebrityDisplaySerializer, TrendingCelebritySerializer
from elasticsearch_dsl.connections import connections
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search, Q
from .constants import *
from rest_framework.views import APIView
from utilities.utils import ResponseViewMixin, get_elasticsearch_connection_params
from .models import CelebrityDisplay, CelebrityDisplayOrganizer
from users.models import StargramzUser, Profession
from users.utils import generate_random_code
from users.fan_views import CelebrityList
from django.db.models import Q, F, Value, Case, When
from django.db.models.functions import Concat
from rest_framework.decorators import list_route
from utilities.permissions import CustomPermission
import ast


class FilterProfessionsV2(FilterProfessions):
    """
        Get the filtered list of Profession version 2
    """

    def list(self, request):
        profession_data = ProfessionFilterSerializerV2(self.profession, many=True)
        return self.jp_response(s_code='HTTP_200_OK', data={'filtered-professions': profession_data.data})


class ProfessionsV2(Professions):
    """
        Get all the Professions for Celebrities version 2
    """
    def get(self, request, *args, **kwargs):
        profession_data = ProfessionSerializerV2(self.profession, many=True)
        return self.jp_response(s_code='HTTP_200_OK', data={'professions': profession_data.data})


class CelebritySuggestionListV2(APIView, ResponseViewMixin):
    """
        Get search result from Elastic Search
    """
    def get(self, request):
        filter_by_name = request.GET.get('s', None)
        connection_params = get_elasticsearch_connection_params()
        connections.create_connection(**connection_params)
        client = Elasticsearch(**connection_params)
        if filter_by_name:
            query_str = Q(
                "multi_match", query=filter_by_name,
                fields=['title', 'first_name', 'last_name', 'nick_name'], type="phrase_prefix"
            )
            search_query = Search(using=client).query(query_str)
            response = search_query.execute()
            professions = []
            celebrities = []
            search_data = {}
            if response:
                for hit in response:
                    if hit.meta['index'] == ES_PROFESSION_INDEX:
                        profession_data = {
                            'id': hit.id,
                            'title': hit.title
                        }
                        if profession_data:
                            professions.append(profession_data)
                    elif hit.meta['index'] == ES_CELEBRITY_INDEX:
                        celebrity_data = {
                            'user_id': hit.user_id,
                            'first_name': hit.first_name,
                            'last_name': hit.last_name,
                            'nick_name': hit.nick_name,
                            'avatar_photo': hit.avatar_photo,
                            'image_url': hit.image_url,
                            'thumbnail_url': hit.thumbnail_url,
                            'professions': hit.professions
                        }
                        if celebrity_data:
                            celebrities.append(celebrity_data)
                search_response = {'professions': professions, 'celebrities': celebrities}
                search_data = SearchSerializer(search_response).data
            return self.jp_response(s_code='HTTP_200_OK', data={'suggestion_list': search_data})
        return self.jp_response(s_code='HTTP_200_OK', data={'suggestion_list': {}})


class CelebrityDisplayView(APIView, ResponseViewMixin):
    """
        Get the 9 stars which is used for display in the homepage in version 2
    """
    def get(self, request):
        profession = request.GET.get('profession', None)
        exclude_condition = {'celebrity': None}
        featured = False
        if profession is '0':
            filter_condition = {'celebrity_display__profession_id': None, 'celebrity_display__featured': True}
            featured = True
        elif profession:
            filter_condition = {'celebrity_display__profession_id': profession}
        else:
            filter_condition = {'celebrity_display__profession': None, 'celebrity_display__featured': False}
        if featured:
            profession = None
            profession_title = "Featured"
        else:
            try:
                profession_title = Profession.objects.get(id=profession).title
            except Exception:
                profession_title = ""

        display_title = CelebrityDisplayOrganizer.objects.values_list('title', flat=True).filter(profession=profession, featured=featured)
        display_title = display_title[0] if display_title else ""

        celebrity_display = CelebrityDisplay.objects.filter(**filter_condition).exclude(**exclude_condition).order_by("order")
        celebrity_data = CelebrityDisplaySerializer(celebrity_display, many=True)
        return self.jp_response(s_code='HTTP_200_OK', data={
            'display_title': display_title,
            'profession': profession_title,
            'celebrity_display': celebrity_data.data
        })


class TrendingStars(APIView, ResponseViewMixin):
    """
        This API will list 10 celebrities according to their popularity
    """
    def get(self, request):

        trending_celebrity = StargramzUser.objects.filter(celebrity_user__admin_approval=True).order_by('-celebrity_user__trending_star_score')[:10]
        data = TrendingCelebritySerializer(trending_celebrity, many=True).data
        return self.jp_response(s_code='HTTP_200_OK', data={'trending_celebrity': data})


class Register(UserRegister):
    def post(self, request):
        request.data["password"] = "@%s" % generate_random_code(size=10)
        return UserRegister.post(self, request)


class CelebrityListV2(CelebrityList):
    """
        The list of celebrities and celebrity search
    """
    def list(self, request):
        query_set = self.query_set.exclude(group_account__admin_approval=True)
        sort = request.GET.get('sort')
        filter_by_lower_rate = request.GET.get('lrate')
        filter_by_upper_rate = request.GET.get('urate')
        filter_by_profession = request.GET.get('profession')
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
                profession_ids = CelebrityList.profession_ids(CelebrityList, x)
                query_set = query_set.filter(celebrity_profession__profession_id__in=profession_ids)
            else:
                return self.jp_error_response('HTTP_400_BAD_REQUEST', 'EXCEPTION', 'Must be a list of values')
        if sort and sort in SORT_LIST:
            sort_list = [k for k in SORT_LIST[sort].split(',')]
            if sort == 'az':
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

    @list_route(methods=['get'], permission_classes=[CustomPermission], authentication_classes=[],
                pagination_class=CelebrityList.pagination_class, serializer_class=CelebrityList.serializer_class)
    def get_list(self, request):
        request.user = None
        return self.list(request)
