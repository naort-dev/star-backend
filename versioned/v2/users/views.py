from django.shortcuts import render
from users.authenticate_views import FilterProfessions, Professions
from users.models import CelebrityProfession, Profession
from .serializer import ProfessionFilterSerializerV2, ProfessionSerializerV2


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
