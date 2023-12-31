from users.authenticate_views import FilterProfessions, Professions, UserRegister, UserDetails, ProfileImages,\
    ChangePassword
from .serializer import ProfessionFilterSerializerV2, ProfessionSerializerV2, SearchSerializer,\
    CelebrityDisplaySerializer, TrendingCelebritySerializer, HomePageVideoSerializer, RegisterUserSerializer, \
    ProfilePictureSerializer, CelebrityApprovalSerializer, CelebrityShareSerializer, CelebrityDashboardSerializer, \
    RecentActivitySerializer, ActivityPublicVisibilitySerializer, ContactSupportSerializerV2, \
    ChangePasswordSerializerV2, TagSerializer, CelebrityTagSerializer
from elasticsearch_dsl.connections import connections
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search, Q
from .constants import *
from rest_framework.views import APIView
from utilities.utils import ResponseViewMixin, get_elasticsearch_connection_params, get_pre_signed_get_url, decode_pk, \
    get_user_role_details, encode_pk
from .models import CelebrityDisplay, CelebrityDisplayOrganizer, HomePageVideo, CelebrityDashboard, CelebrityTag
from users.models import StargramzUser, Profession, Celebrity, AdminReferral, FanRating, SettingsNotifications,\
    REMINDER_MAIL_COUNT, ProfileImage, Referral, RecentActivity, ACTIVITY_TYPES, SocialMediaLinks, UserRoleMapping
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
from utilities.konstants import ROLES
from .tasks import welcome_email_version_2, remove_profile_images_from_s3, celebrity_dashboard_update
from .utils import date_format_conversion, recent_deposit_amount, apply_the_checks
from rest_framework.permissions import IsAuthenticated
from utilities.authentication import CustomAuthentication
from utilities.utils import removefromdict, sent_email, get_the_role_of_user,\
    delete_celebrity_details_of_user
from utilities.pagination import CustomOffsetPagination
from rest_framework.viewsets import GenericViewSet
from datetime import datetime, timedelta
from stargramz.models import Stargramrequest
import pytz
from role.models import Role
from users.tasks import welcome_email
from job.tasks import send_message_to_slack
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

        trending_celebrity = StargramzUser.objects.filter(
            celebrity_user__admin_approval=True, celebrity_user__star_approved=True,
            is_active=True, temp_password=False).order_by(
            '-celebrity_user__trending_star_score')[:10]
        data = TrendingCelebritySerializer(trending_celebrity, many=True).data
        return self.jp_response(s_code='HTTP_200_OK', data={'trending_celebrity': data})


class Register(UserRegister):
    def post(self, request):
        if request.data['role'] == ROLES.celebrity:
            request.data["password"] = "@%s" % generate_random_code(size=10)
        response = UserRegister.post(self, request)
        if response.data['status'] == 200:
            try:
                user = StargramzUser.objects.get(id=decode_pk(response.data['data']['user']['id']))
                user.temp_password = True
                user.expiry_date = date_format_conversion(request.data.get('expiry_date', None))
                user.reminder_mail_count = REMINDER_MAIL_COUNT.first_mail
                user.save()
            except Exception as e:
                print(str(e))
                pass
        return response

    def put(self, request):
        try:
            old_user = StargramzUser.objects.get(id=request.user.id)
            role = get_the_role_of_user(old_user)
            if request.data.get('role', None) and role and request.data[
                'role'] != role.code and role.code == ROLES.celebrity:
                user = delete_celebrity_details_of_user(old_user)
            else:
                user = request.user
            serializer = RegisterUserSerializer(data=request.data, context={'user': user})
            if serializer.is_valid():
                user = serializer.save()

                is_complete = False
                roles = request.data.get('role', None)
                if roles:
                    role = Role.objects.get(code=roles)
                if roles == ROLES.fan:
                    is_complete = True

                user_role, created = UserRoleMapping.objects.get_or_create(
                    user=user,
                    role=role,
                    is_complete=is_complete
                )
                if is_complete:
                    welcome_email.delay(user.pk)
                    # when a fan created, a message will send to the slack
                    slack_template = "new_user_fan"
                    slack_ctx = {
                        "fan_name": user.get_short_name()
                    }
                    send_message_to_slack.delay(slack_template, slack_ctx)

                role_details = get_user_role_details(user)
                try:
                    user.authentication_token = Token.objects.get(user_id=user.id)
                except:
                    pass
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
        # exclude_condition = {'group_account__admin_approval': True, 'celebrity_user__profile_video': ''}
        # query_set = self.query_set.filter(is_active=True, temp_password=False).exclude(**exclude_condition)
        query_set = self.query_set.filter(is_active=True, temp_password=False).exclude(
            group_account__admin_approval=True
        )
        sort = request.GET.get('sort')
        filter_by_lower_rate = request.GET.get('lrate')
        filter_by_upper_rate = request.GET.get('urate')
        filter_by_profession = request.GET.get('profession')
        filter_by_tag = request.GET.get('tag')
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

        if filter_by_tag:
            try:
                tag_id = decode_pk(filter_by_tag)
            except:
                pass
            if tag_id:
                query_set = query_set.filter(tag_user__tag_id=tag_id)

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
        response = UserDetails.get_details(
            self, request, pk, user_followed=user_followed, user_logged_in=user_logged_in)
        response = self.append_profile_video(response, pk, user_logged_in)
        return response

    def retrieve(self, request, pk):
        response = UserDetails.retrieve(self, request, pk)
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

    def referral_code(self, pk):
        try:
            referral = Referral.objects.get(referee_id=pk)
            return referral.referrer.referral_code
        except:
            return None

    def celebrity_tags(self, celebrity):
        tags = CelebrityTag.objects.filter(user_id=celebrity)
        serializer = CelebrityTagSerializer(tags, many=True)

        return serializer.data

    def append_profile_video(self, response, pk, user_logged_in):
        if response.data.get("status") == 200:
            profile_video = None
            duration = None
            try:
                pk = self.verify_hash_token(pk)
            except:
                pass
            try:
                config = Config.objects.get(key='authentication_videos')
                celebrity = Celebrity.objects.get(user_id=pk)
                if celebrity.profile_video:
                    profile_video = get_pre_signed_get_url(celebrity.profile_video, config.value)
                    duration = celebrity.duration
                # else:
                #     if user_logged_in != pk:
                #         return self.jp_error_response(
                #             'HTTP_400_BAD_REQUEST', 'INVALID_SIGNUP',
                #             'The celebrity you are looking for is currently unavailable'
                #         )
            except Exception as e:
                print(str(e))
                pass
            if response.data['data'].get('celebrity_details', None):
                average_response_time, avg_response_value = self.average_response_time(pk)
                current_rating = response.data['data']['celebrity_details'].get('rating', None)
                rating = self.rating_checking(pk, current_rating)
                notification = celebrity.user.settings_user.all().first()
                celebrity_tags = self.celebrity_tags(pk)
                response.data['data']['celebrity_details'].update(
                    {
                        'profile_video': profile_video,
                        'duration': duration,
                        'average_response_time': average_response_time,
                        'average_response_value': avg_response_value,
                        'rating': rating,
                        'used_referral_code': self.referral_code(pk),
                        'has_profile_video': True if profile_video else False,
                        'has_password': False if celebrity.user.temp_password else True,
                        'has_phone_number': True if notification and notification.mobile_number else False,
                        'allow_booking': True if profile_video and not celebrity.user.temp_password else False,
                        'tags': celebrity_tags
                    }
                )

        return response

    def update(self, request, pk):
        response = UserDetails.update(self, request, pk)
        if request.data['user_details'].get('social_links', None):
            response = self.save_social_links_of_user(
                response, request.data['user_details']['social_links'], request.user)

        if request.data['celebrity_details'].get('tags', None):
            response = self.save_user_tags(response, request.data['celebrity_details']['tags'], request.user)

        response = self.append_profile_video(response, pk, request.user)
        return response

    def save_social_links_of_user(self, response, links, user):
        for link in links:
            social_link, created = SocialMediaLinks.objects.get_or_create(
                user=user,
                social_link_key=link.get('social_link_key'),
            )
            social_link.social_link_value = link.get('social_link_value')
            social_link.save()
        response.data['data']['user']['social_links'] = links
        return response

    def save_user_tags(self, response, tags, user):
        CelebrityTag.objects.filter(user=user).delete()
        for tag in tags:
            CelebrityTag.objects.create(user_id=user.id, tag_id=tag)
        celebrity_tags = CelebrityTag.objects.filter(user=user)
        tag_serializer = CelebrityTagSerializer(celebrity_tags, many=True)

        response.data['data']['celebrity_details']['tags'] = tag_serializer.data

        return response


class CelebrityManagementV2(CelebrityManagement):

    def __init__(self, *args, **kwargs):
        self.welcome_mail = welcome_email_version_2
        super().__init__(*args, **kwargs)

    def post(self, request):
        user = request.user
        try:
            referral_code = request.data.get("referral_code", None)
            referral = AdminReferral.objects.get(referral_code=referral_code, activate=True)
            user.admin_approval_referral_code = referral
            user.save()
        except Exception:
            pass
        response = CelebrityManagement.post(self, request)
        if response.data['status'] == 200:
            user.expiry_date = None
            user.save()
            try:
                config = Config.objects.get(key='authentication_videos')
                celebrity = Celebrity.objects.get(user_id=user.id)
                if celebrity.profile_video:
                    response.data['data']['celebrity']['profile_video'] = get_pre_signed_get_url(
                        celebrity.profile_video, config.value
                    )
                celebrity.star_approved = True
                celebrity.save()
            except Exception as e:
                print(str(e))
                pass

        return response


class StargramzAutocomplete(autocomplete.Select2QuerySetView):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.query_set = StargramzUser.objects.filter(
            celebrity_user__admin_approval=True, is_active=True, celebrity_user__star_approved=True, temp_password=False
        )
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


class ProfileImagesV2(ProfileImages):
    def post(self, request):
        user = request.user
        images = ProfileImage.objects.values_list('id', flat=True).filter(user_id=user.id)
        if images:
            images = list(images)
            remove_profile_images_from_s3.delay(images)
        response = ProfileImages.post(self, request)
        if response.data['status'] == 200:
            response.data['data']['avatar_photo'] = ProfilePictureSerializer(user.avatar_photo).data

        return response


class CelebrityApproval(APIView, ResponseViewMixin):

    def post(self, request):

        serializer = CelebrityApprovalSerializer(data=request.data)
        rate = request.data.get('rate', None)
        data = {}
        if serializer.is_valid():
            celebrity, user = serializer.validated_data
            if rate:
                celebrity.rate = rate
                celebrity.save()
            (token, created) = Token.objects.get_or_create(user=user)
            data['authentication_token'] = token.key
            data['user_id'] = encode_pk(user.id)

            celebrity.star_approved = True
            celebrity.admin_approval = True
            user.reset_id = None

            user.save()
            celebrity.save()
            return self.jp_response(s_code='HTTP_200_OK', data=data)
        else:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_CODE',
                                          self.error_msg_string(serializer.errors))


class CelebrityShare(APIView, ResponseViewMixin):
    authentication_classes = (CustomAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)

    def post(self, request):
        serializer = CelebrityShareSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(request.user)
            return self.jp_response('HTTP_200_OK', data={"comments": "Added share details"})
        else:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_CODE',
                                          self.error_msg_string(serializer.errors))


class CelebrityDashboardView(APIView, ResponseViewMixin):
    authentication_classes = (CustomAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)

    def get(self, request):
        try:
            dashboard = CelebrityDashboard.objects.get(user_id=request.user.id)
            data = CelebrityDashboardSerializer(dashboard).data
            amount, date = recent_deposit_amount(request.user, dashboard)
            data = apply_the_checks(request.user, data)  # apply all the checks required for the front-end
            data.update(
                {
                    'recent_deposit_amount': amount,
                    'recent_deposit_date': date
                }
            )
            keys = ['id', 'created_date', 'modified_date', 'last_updated_by_update_API']
            data = removefromdict(data, keys)
            return self.jp_response('HTTP_200_OK', data={"dashboard": data})
        except Exception as e:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_CODE', str(e))


class DashboardUpdateView(APIView, ResponseViewMixin):
    authentication_classes = (CustomAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)

    def get(self, request):
        celebrity_dashboard_update(request.user.id)
        return self.jp_response('HTTP_200_OK', data="Dashboard Updating")


class RecentActivityView(GenericViewSet, ResponseViewMixin):
    authentication_classes = (CustomAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)
    pagination_class = CustomOffsetPagination
    serializer_class = RecentActivitySerializer

    def get_serializer_context(self):
        return {"user": self.user}

    @detail_route(methods=['get'], permission_classes=[CustomPermission], authentication_classes=[])
    def public_list(self, request, query_set=None, pk=None):
        page_no = request.GET.get('offset', None)
        booking_id = None
        if pk:
            try:
                booking_id = decode_pk(pk)
            except:
                pass
            if booking_id:
                try:
                    booking = Stargramrequest.objects.get(id=booking_id)
                except Stargramrequest.DoesNotExist:
                    return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_SIGNUP', 'Invalid Booking')
                if booking:
                    query_set = RecentActivity.objects.filter(request_id=booking_id).exclude(
                        activity_type=ACTIVITY_TYPES.video
                    )
                    if request.user.id:
                        if request.user == booking.celebrity or request.user == booking.fan:
                            query_set = query_set
                        else:
                            query_set = query_set.filter(public_visibility=True)
                    else:
                        query_set = query_set.filter(public_visibility=True)
        if request.user:
            self.user = request.user

        if query_set:
            query_set = query_set.order_by('-created_date')
            if page_no:
                page = self.paginate_queryset(query_set.distinct())
                serializer = self.get_serializer(page, many=True)
                response = self.paginator.get_paginated_response(serializer.data, key_name='recent_activities')
            else:
                query_set = query_set.distinct()
                serializer = self.get_serializer(query_set, many=True)
                response = self.jp_response(
                    s_code='HTTP_200_OK', data={'recent_activities': serializer.data, 'count': query_set.count()}
                )
            return response
        else:
            return self.jp_response( s_code='HTTP_200_OK', data={'recent_activities': [], 'count': 0})

    def list(self, request):
        filter_by_role = request.GET.get('role', None)
        current_date = datetime.now(pytz.UTC)
        query_set = None
        if filter_by_role:
            if filter_by_role == CELEBRITY:
                query_set = RecentActivity.objects.filter(
                    activity_to_user=request.user, is_celebrity_activity=False
                )
            elif filter_by_role == FAN:
                comment_activity = RecentActivity.objects.filter(
                    activity_to_user=request.user, is_celebrity_activity=True,
                    activity_type=ACTIVITY_TYPES.comment,
                    created_date__range=(current_date - timedelta(days=14), current_date)
                )
                video_activity = RecentActivity.objects.filter(
                    activity_to_user=request.user, is_celebrity_activity=True,
                    activity_type=ACTIVITY_TYPES.video
                )
                query_set = comment_activity | video_activity

        return self.public_list(request, query_set, pk=None)

    def retrieve(self, request, pk):
        return self.public_list(request, query_set=None, pk=pk)


class ActivityPublicVisibility(APIView, ResponseViewMixin):
    authentication_classes = (CustomAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)

    def post(self, request):
        request.data.update(
            {
                'activity_to_user': request.user.id,
                'activity_from_user': request.user.id
            }
        )
        serializer = ActivityPublicVisibilitySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return self.jp_response(s_code='HTTP_200_OK', data='success')
        else:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_CODE',
                                          self.error_msg_string(serializer.errors))


class ContactSupportV2(APIView, ResponseViewMixin):
    """
        Sent email to support from the Fans request details screen
    """

    authentication_classes = (CustomAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)

    def post(self, request):
        serializer = ContactSupportSerializerV2(data=request.data)
        if serializer.is_valid():
            support_email = Config.objects.get(key='support_email').value

            subject = 'Starsona Contact Support'
            template = 'contact_support_v2'
            ctx = {
                'username': request.user.get_short_name(),
                'email': request.user.email,
                'topic': serializer.validated_data.get('topic'),
                'comments': serializer.validated_data.get('comments'),
            }
            sent_email(support_email, subject, template, ctx)
            return self.jp_response(s_code='HTTP_200_OK', data='Submitted your comments to our support team')
        else:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_LOGIN', self.error_msg_string(serializer.errors))


class ChangePasswordV2(ChangePassword):
    serializer_class = ChangePasswordSerializerV2


class SettingsViewed(APIView, ResponseViewMixin):
    authentication_classes = (CustomAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)

    def post(self, request):
        try:
            settings = SettingsNotifications.objects.get(user_id=request.user.id)
            settings.is_viewed = True
            settings.save()
            return self.jp_response(s_code='HTTP_200_OK', data='successful')
        except Exception as e:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_LOGIN', str(e))


class TagView(APIView, ResponseViewMixin):
    authentication_classes = (CustomAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)

    def post(self, request):
        tags = request.data.get('tags', None)
        serializer = TagSerializer(data=tags, many=True)
        if serializer.is_valid():
            serializer.save()

            return self.jp_response(s_code='HTTP_200_OK', data={'tags': serializer.data})
        else:
            error_list = []
            for error in serializer.errors:
                if error:
                    error_list.append(self.error_msg_string(error))

            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_LOGIN', error_list)
