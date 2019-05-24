from users.authenticate_views import FilterProfessions, Professions, UserRegister, UserDetails
from .serializer import ProfessionFilterSerializerV2, ProfessionSerializerV2, SearchSerializer,\
    CelebrityDisplaySerializer, TrendingCelebritySerializer, HomePageVideoSerializer, RegisterUserSerializer
from elasticsearch_dsl.connections import connections
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search, Q
from .constants import *
from rest_framework.views import APIView
from utilities.utils import ResponseViewMixin, get_elasticsearch_connection_params, get_pre_signed_get_url, decode_pk, \
    get_user_role_details
from .models import CelebrityDisplay, CelebrityDisplayOrganizer, HomePageVideo
from users.models import StargramzUser, Profession, Celebrity, AdminReferral, FanRating, SettingsNotifications
from users.utils import generate_random_code
from users.fan_views import CelebrityList
from django.db.models import Q, F, Value, Case, When
from django.db.models.functions import Concat
from rest_framework.decorators import list_route
from utilities.permissions import CustomPermission
import ast
from users.celebrity_views import CelebrityManagement
from config.models import Config
from rest_framework.decorators import detail_route
from dal import autocomplete
from hashids import Hashids
from users.serializer import RegisterSerializer, NotificationSettingsSerializerEncode
from rest_framework.authtoken.models import Token
hashids = Hashids(min_length=8)


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
        parent = request.GET.get("parent", None)
        if parent:
            profession = Profession.objects.filter(parent__isnull=False)
        else:
            profession = self.profession
        profession_data = ProfessionSerializerV2(profession, many=True)
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
        videos = HomePageVideo.objects.all()
        home_page_serializer = HomePageVideoSerializer(videos, many=True)

        return self.jp_response(s_code='HTTP_200_OK', data={
            'display_title': display_title,
            'profession': profession_title,
            'celebrity_display': celebrity_data.data,
            'home_page_videos': home_page_serializer.data
        })


class TrendingStars(APIView, ResponseViewMixin):
    """
        This API will list 10 celebrities according to their popularity
    """
    def get(self, request):

        trending_celebrity = StargramzUser.objects.filter(celebrity_user__admin_approval=True, is_active=True).order_by('-celebrity_user__trending_star_score')[:10]
        data = TrendingCelebritySerializer(trending_celebrity, many=True).data
        return self.jp_response(s_code='HTTP_200_OK', data={'trending_celebrity': data})


class Register(UserRegister):
    def post(self, request):
        request.data["password"] = "@%s" % generate_random_code(size=10)
        response = UserRegister.post(self, request)
        if response.data['status'] == 200:
            try:
                user = StargramzUser.objects.get(id=decode_pk(response.data['data']['user']['id']))
                user.temp_password = True
                user.save()
            except:
                pass
        return response

    def put(self, request):
        try:
            user = StargramzUser.objects.get(id=request.user.id)
            serializer = RegisterUserSerializer(data=request.data)
            if serializer.is_valid():
                if StargramzUser.objects.filter(email=serializer.validated_data['email']).exclude(id=user.id).exists():
                    return self.jp_error_response('HTTP_400_BAD_REQUEST', 'USER_EXISTS', 'Email already registered')
                user.email = serializer.validated_data['email']
                user.first_name = serializer.validated_data['first_name']
                user.last_name = serializer.validated_data['last_name']
                user.nick_name = serializer.validated_data['nick_name']
                user.save()
                role_details = get_user_role_details(user)
                user.authentication_token = Token.objects.filter(user_id=user.id).first()
                data = RegisterSerializer(user).data
                (notifications, created) = SettingsNotifications.objects.get_or_create(user_id=user.id)
                data['notification_settings'] = NotificationSettingsSerializerEncode(notifications).data
                data['role_details'] = role_details
                return self.jp_response(s_code='HTTP_200_OK', data={'user': data})
            else:
                return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_CREATE',
                                              self.error_msg_string(serializer.errors))
        except StargramzUser.DoesNotExist:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_USER',
                                          'Email is not registered with Starsona.')


class CelebrityListV2(CelebrityList):
    """
        The list of celebrities and celebrity search
    """
    def list(self, request):
        query_set = self.query_set.filter(is_active=True).exclude(group_account__admin_approval=True)
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


class UserDetailsV2(UserDetails):

    @detail_route(methods=['get'], permission_classes=[CustomPermission], authentication_classes=[])
    def get_details(self, request, pk=None, user_followed=None, user_logged_in=None):
        response = UserDetails.get_details(self, request, pk, user_followed=user_followed, user_logged_in=user_logged_in)
        response = self.append_profile_video(response, pk)
        return response

    def retrieve(self, request, pk):
        response = UserDetails.retrieve(self, request, pk)
        response = self.append_profile_video(response, pk)
        return response

    def average_response_time(self, celebrity):
        """
        This function should take the average_response_time from the celebrity table
        :return:
        """
        try:
            celebrity = Celebrity.objects.get(user_id=celebrity)
        except Exception as e:
            print("Error in average response time function")
            average_response_time = None
        else:
            time = celebrity.average_response_time
            if time == 0:
                # average_response_time = Config.objects.get(key='average_response_time').value
                average_response_time = None
            elif time % 1 > 0.5:
                average_response_time = str((time//1)+1)
            else:
                average_response_time = str(time//1)
        if average_response_time:
            if int(average_response_time) > 1:
                response = "%s Days" % average_response_time
            else:
                response = "One Day"
        else:
            response = ""
        return response, average_response_time

    def rating_checking(self, celebrity, current_rating):
        final_rating = current_rating
        if current_rating:
            if float(current_rating) < 4.0:
                total_ratings = FanRating.objects.filter(celebrity_id=celebrity).count()
                if total_ratings < 10:
                    final_rating = ""
        return final_rating

    def append_profile_video(self, response, pk):
        if response.data.get("status") == 200:
            profile_video = None
            try:
                pk = self.verify_hash_token(pk)
            except:
                pass
            try:
                config = Config.objects.get(key='authentication_videos')
                celebrity = Celebrity.objects.get(user_id=pk)
                if celebrity.profile_video:
                    profile_video = get_pre_signed_get_url(celebrity.profile_video, config.value)
            except Exception as e:
                print(str(e))
                pass
            if response.data['data'].get('celebrity_details', None):
                average_response_time, avg_response_value = self.average_response_time(pk)
                current_rating = response.data['data']['celebrity_details'].get('rating', None)
                rating = self.rating_checking(pk, current_rating)
                response.data['data']['celebrity_details'].update(
                    {
                        'profile_video': profile_video,
                        'average_response_time': average_response_time,
                        'average_response_value': avg_response_value,
                        'rating': rating
                    }
                )
        return response


class CelebrityManagementV2(CelebrityManagement):

    def post(self, request):
        user = request.user
        try:
            referral_code = request.data.get("referral_code", None)
            referral = AdminReferral.objects.get(referral_code=referral_code, activate=True)
            user.admin_approval_referral_code = referral
            user.save()
        except Exception:
            pass
        return CelebrityManagement.post(CelebrityManagement, request)


class StargramzAutocomplete(autocomplete.Select2QuerySetView):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.query_set = StargramzUser.objects.filter(celebrity_user__admin_approval=True, is_active=True)
        self.query_set = self.query_set.annotate(sort_name=Case(
            When(Q(nick_name__isnull=False) & ~Q(nick_name=''), then=F('nick_name')),
            default=Concat('first_name', Value(' '), 'last_name')))

    def get_queryset(self):
        profession = self.forwarded.get("profession", None)
        if not self.request.user.is_superuser:
            return StargramzUser.objects.none()

        if profession:
            self.query_set = self.query_set.filter(
                Q(celebrity_profession__profession=profession) | Q(celebrity_profession__profession__parent=profession)
            )

        if self.q:
            self.query_set = self.query_set.filter(sort_name__icontains=self.q)
        return self.query_set.order_by('sort_name').distinct()

    def get_result_label(self, result):
        return result.sort_name

    def get_selected_result_label(self, result):
        return result.sort_name
