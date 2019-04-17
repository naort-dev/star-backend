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
