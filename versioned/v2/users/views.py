from django.shortcuts import render
from users.authenticate_views import FilterProfessions, Professions
from users.models import CelebrityProfession, Profession
from .serializer import ProfessionFilterSerializerV2, ProfessionSerializerV2, SearchSerializer
from rest_framework.views import APIView
from utilities.mixins import ResponseViewMixin
from elasticsearch_dsl.connections import connections
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search, Q
from .constants import *
import os


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
        connections.create_connection()
        client = Elasticsearch(hosts=[os.environ.get('ES_HOST_NAME')])
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
