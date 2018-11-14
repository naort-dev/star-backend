from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView
from rest_framework import viewsets
from utilities.mixins import ResponseViewMixin
from .serializer import OccasionSerializer, StargramzSerializer, StargramzVideoSerializer, StargramzRetrieveSerializer,\
    RequestStatusSerializer, ReportAbuseSerializer, OccasionCreateSerializer, CommentSerializer, \
    CommentReplySerializer, ReactionSerializer
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from utilities.konstants import ROLES, NOTIFICATION_TYPES
from config.models import Config
from config.constants import *
from utilities.constants import BASE_URL
from users.models import StargramzUser, Celebrity, UserRoleMapping, ProfileImage, VanityUrl, FanRating
from users.serializer import CelebrityRatingSerializer
import json
from .models import Stargramrequest, StargramVideo, OccasionRelationship, Occasion, STATUS_TYPES, REQUEST_TYPES,\
    VIDEO_STATUS, Comment
from rest_framework.viewsets import ViewSet, GenericViewSet
from utilities.pagination import CustomOffsetPagination
import datetime
from utilities.utils import datetime_range, get_pre_signed_get_url, check_user_role, upload_image_s3, get_s3_public_url
from utilities.permissions import CustomPermission
from rest_framework.decorators import detail_route
from django.db.models import Q
import uuid
import magic
import os
import ast
from difflib import get_close_matches
from .constants import *
from job.tasks import generate_video_thumbnail, notify_email, combine_video_clips, convert_audio
from payments.models import StarsonaTransaction, TRANSACTION_STATUS
from django.utils import timezone
from hashids import Hashids
from notification.tasks import send_notification
from payments.tasks import create_request_refund
from payments.constants import SECRET_KEY
from django.http import HttpResponsePermanentRedirect
import stripe
hashids = Hashids(min_length=8)

API_KEY = SECRET_KEY
stripe.api_key = API_KEY


class OccasionList(APIView, ResponseViewMixin):

    def get(self, request):
        type_id = request.GET.get("type")
        req_type = int(type_id) if type_id and int(type_id) in [1, 2, 3] else 1
        occasion = Occasion.objects.filter(request_type=req_type, visibility=True).order_by('title')
        serializer = OccasionSerializer(occasion, many=True)
        return self.jp_response('HTTP_200_OK', data={"occasion_list": serializer.data})

    def post(self, request):
        serializer = OccasionCreateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(visibility=False, type=2)
            return self.jp_response('HTTP_200_OK', data={"occasion": serializer.data})
        return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_LOGIN', self.error_msg_string(serializer.errors))


class StargramzRequest(viewsets.ViewSet, ResponseViewMixin):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)

    def create(self, request):
        """
            Create a Stargramz Request and Audio file save
        """
        mutable = request.data._mutable
        request.data._mutable = True
        request.data['occasion'] = request.data['occasion'] if 'occasion' in request.data and\
                                                               len(request.data['occasion']) > 0 else 34
        try:
            occasions = Occasion.objects.get(id=request.data['occasion']).title
        except Exception:
            occasions = 'Occasion'
        request.data['public_request'] = True if 'public_request' not in request.data \
            else request.data['public_request'].title()
        try:
            fanuser = StargramzUser.objects.get(username=request.user)
            request.data['fan'] = fanuser.id
        except StargramzUser.DoesNotExist:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_SIGNUP', 'Invalid Signup User')
        try:
            celebrity = Celebrity.objects.get(user_id=request.data['celebrity'])
        except Celebrity.DoesNotExist:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_SIGNUP', 'Not an celebrity user')
        request.data['booking_title'] = self.generate_title(request.data, celebrity, occasions)
        request.POST._mutable = mutable
        serializer = StargramzSerializer(data=request.data)
        if serializer.is_valid():
            request_created = serializer.save()
            process_audio = False

            for INPUT_FILE_LABEL in INPUT_FILE_LABELS:
                if INPUT_FILE_LABEL in request.FILES:
                    file = request.FILES[INPUT_FILE_LABEL]
                    # file_extension = self.mime_type_validation_and_extension(file)
                    filename, file_extension = os.path.splitext(str(file))
                    if not file_extension:
                        request_created.delete()
                        return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_CREATE',
                                                      'File Type not of able choices')
                    file_name = self.handle_uploaded_file(file, str(file_extension))
                    if str(file_extension) == '.webm':
                        process_audio = True
                    setattr(request_created, INPUT_FILE_LABEL, file_name)
                    request_created.save()
            if process_audio:
                convert_audio.delay(request_created.id)
            data = StargramzRetrieveSerializer(request_created).data
            return self.jp_response('HTTP_200_OK', data={'stargramz_response': data})
        else:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_LOGIN',
                                          self.error_msg_string(serializer.errors))

    def handle_uploaded_file(self, file, file_extension):
        FILE_SAVE = AUDIO_SAVE
        file_name = str(uuid.uuid4())+file_extension
        s3_file_name = 'audio/%s' % file_name

        if not os.path.exists(FILE_SAVE):
            os.makedirs(FILE_SAVE)

        FILE_LOCATION = FILE_SAVE + file_name
        with open(FILE_LOCATION, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
            destination.close()

        upload_image_s3(FILE_LOCATION, s3_file_name)
        return s3_file_name

    def mime_type_validation_and_extension(self, file):
        mime = magic.Magic(mime=True)
        mime_type = mime.from_buffer(file.read())
        if mime_type in AUDIO_FILE_TYPES:
            filename, file_extension = os.path.splitext(str(file))
            return file_extension
        else:
            return False

    def delete_file(self, file):

        FILE_SAVED = AUDIO_SAVE
        try:
            os.remove(FILE_SAVED+file)
        except Exception:
            pass

    def update(self, request, pk):
        """
            Update a Stargramz Request
        """
        mutable = request.data._mutable
        request.data._mutable = True
        request.data['occasion'] = request.data['occasion'] if 'occasion' in request.data and \
                                                               len(request.data['occasion']) > 0 else 34
        request.data['public_request'] = True if 'public_request' not in request.data \
            else request.data['public_request'].title()
        try:
            fanuser = StargramzUser.objects.get(username=request.user)
            request.data['fan'] = fanuser.id
        except StargramzUser.DoesNotExist:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_SIGNUP', 'Invalid Signup User')
        try:
            celebrity = Celebrity.objects.get(user_id=request.data['celebrity'])
        except Celebrity.DoesNotExist:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_SIGNUP', 'Not an celebrity user')
        try:
            star_request = Stargramrequest.objects.get(id=pk, fan_id=fanuser.id)
        except Stargramrequest.DoesNotExist:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_UPDATE', 'Invalid update details provided')

        try:
            edit_time = Config.objects.get(key='booking_edit_time').value
        except Exception:
            edit_time = REQUEST_EDIT_ALLOWED_TIME
        try:
            occasions = Occasion.objects.get(id=request.data['occasion']).title
        except Exception:
            occasions = 'Occasion'
        request.data['booking_title'] = self.generate_title(request.data, celebrity, occasions)
        try:
            transaction = StarsonaTransaction.objects.get(starsona_id=star_request.id)
            if timezone.now() > transaction.created_date + datetime.timedelta(minutes=int(edit_time)):
                return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_UPDATE',
                                              'Sorry; You can no longer update this request,'
                                              ' as we have started processing it')
        except StarsonaTransaction.DoesNotExist:
            pass
        request.POST._mutable = mutable
        serializer = StargramzSerializer(data=request.data)
        if serializer.is_valid():
            process_audio = False
            for INPUT_FILE_LABEL in INPUT_FILE_LABELS:

                # For saving new audio files and removing old ones.
                if INPUT_FILE_LABEL in request.FILES:
                    file = request.FILES[INPUT_FILE_LABEL]
                    filename, file_extension = os.path.splitext(str(file))
                    # file_extension = self.mime_type_validation_and_extension(file)
                    if not file_extension:
                        return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_CREATE',
                                                      'File Type not of able choices')
                    file_name = self.handle_uploaded_file(file, str(file_extension))
                    if str(file_extension) == '.webm':
                        process_audio = True
                    input = getattr(star_request, INPUT_FILE_LABEL)
                    self.delete_file(input)
                    setattr(star_request, INPUT_FILE_LABEL, file_name)

                # For removing existing audio files.
                if 'remove_audios' in request.data and INPUT_FILE_LABEL in request.data['remove_audios']:
                    file_name = None
                    input = getattr(star_request, INPUT_FILE_LABEL)
                    self.delete_file(input)
                    setattr(star_request, INPUT_FILE_LABEL, file_name)
            if process_audio:
                convert_audio.delay(star_request.id)
            star_request.occasion_id = request.data['occasion']
            star_request.request_details = request.data['request_details']
            star_request.public_request = request.data['public_request']
            star_request.booking_title = request.data['booking_title']
            star_request.save()
            data = StargramzRetrieveSerializer(star_request).data
            return self.jp_response('HTTP_200_OK', data={'stargramz_response': data})
        else:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_LOGIN',
                                          self.error_msg_string(serializer.errors))

    def get(self, request, pk):
        """
            Get the details of Stargramz Request
        """
        try:
            pk = hashids.decode(pk)[0]
        except Exception:
            pk = pk

        try:
            user = StargramzUser.objects.get(username=request.user)
        except StargramzUser.DoesNotExist:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_SIGNUP', 'Invalid Signup User')
        try:
            star_request = Stargramrequest.objects.get(Q(id=pk), Q(fan_id=user.id) | Q(celebrity_id=user.id))
        except Stargramrequest.DoesNotExist:
            return self.jp_error_response(
                'HTTP_400_BAD_REQUEST',
                'INVALID_CODE',
                'You are not allowed to view the request'
            )
        data = StargramzRetrieveSerializer(star_request).data
        return self.jp_response('HTTP_200_OK', data={'stargramz_response': data})

    def generate_title(self, request, celebrity, occasion):
        """
            Generate the title for Booking
        """
        details = json.loads(request['request_details'])
        request_type = 1
        if 'request_type' in request:
            request_type = int(request['request_type'])

        titles = {
            1: '%s video shout-out from %s' % (occasion, celebrity.user.get_short_name()),
            2: '%s announcement from %s' % (occasion, celebrity.user.get_short_name()),
            3: '%s' % (details['question'] if 'question' in details and len(details['question']) > 0 else
                       'Q&A for %s' % celebrity.user.get_short_name())
        }

        return titles.get(request_type)

class ChangeRequestStatus(APIView, ResponseViewMixin):
    """
        The Change status of Request
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)

    def post(self, request):
        try:
            user = StargramzUser.objects.get(username=request.user)
        except StargramzUser.DoesNotExist:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_SIGNUP', 'Invalid Signup User')
        serializer = RequestStatusSerializer(data=request.data)
        if serializer.is_valid():
            try:
                Stargramrequest.objects.get(
                    id=request.data['id'],
                    request_status__in=[
                        STATUS_TYPES.video_approval,
                        STATUS_TYPES.completed,
                        STATUS_TYPES.cancelled
                    ]
                )
                return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_SIGNUP',
                                              'Request cannot be modified at this time.')
            except Stargramrequest.DoesNotExist:
                pass

            try:
                star_request = Stargramrequest.objects.get(
                    Q(id=request.data['id'])
                    & (Q(celebrity_id=user.id) | Q(fan_id=user.id))
                )
            except Stargramrequest.DoesNotExist:
                return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_SIGNUP',
                                              'Request does not exist with this user')
            star_request.request_status = int(request.data['status'])
            if 'comment' in request.data:
                star_request.comment = request.data['comment']
            star_request.save()
            if star_request.request_status == STATUS_TYPES.cancelled:
                create_request_refund.delay()
                if user.id == star_request.celebrity.id:
                    data = {'id': star_request.id, 'type': NOTIFICATION_TYPES.fan_celebrity_cancelled_details,
                            'role': ROLES.fan}
                    send_notification.delay(star_request.fan.id,
                                            NOTIFICATION_REQUEST_CELEBRITY_CANCEL_TITLE,
                                            NOTIFICATION_REQUEST_CELEBRITY_CANCEL_BODY,
                                            data, field='fan_starsona_videos')
                else:
                    data = {'id': star_request.id, 'type': NOTIFICATION_TYPES.fan_celebrity_cancelled_details,
                            'role': ROLES.celebrity}
                    send_notification.delay(star_request.celebrity.id,
                                            NOTIFICATION_REQUEST_FAN_CANCEL_TITLE,
                                            NOTIFICATION_REQUEST_FAN_CANCEL_BODY % (star_request.fan.get_short_name()),
                                            data, field='celebrity_starsona_request')
            data = StargramzRetrieveSerializer(star_request).data
            return self.jp_response('HTTP_200_OK', data={'change_status': data})
        else:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_LOGIN',
                                          self.error_msg_string(serializer.errors))


class RequestList(GenericViewSet, ResponseViewMixin):
    """
        The list of celebrities and celebrity search
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)
    pagination_class = CustomOffsetPagination
    serializer_class = StargramzRetrieveSerializer

    def list(self, request):
        """
            Stargramz Request List
        """
        try:
            user = StargramzUser.objects.get(username=request.user)
        except StargramzUser.DoesNotExist:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_SIGNUP', 'Invalid Signup User')
        mappings = UserRoleMapping.objects.get(user=user)

        role_list = {ROLES.celebrity: 'celebrity_id', ROLES.fan: 'fan_id'}

        user_role = request.GET['role'] if 'role' in request.GET else None
        role = user_role if user_role and user_role in ['fan_id', 'celebrity_id'] else role_list[mappings.role.code]

        status_list = [[2, 3], [5], [6]] if role == 'celebrity_id' else [[2, 3, 1], [5], [6]]
        # role = 'celebrity_id' if mappings.role.code == ROLES.celebrity else 'fan_id'
        # status_list = [[2, 3], [5], [6]] if mappings.role.code == ROLES.celebrity else [[2, 3, 1], [5], [6]]

        if mappings.role.code == ROLES.celebrity:
            user.unseen_bookings = 0
            user.save()

        # status_list = [[2, 3], [5], [6]]
        custom_filter = {role: user.id}
        query_set = Stargramrequest.objects.filter(**custom_filter)\
            .select_related('occasion', 'fan', 'celebrity')\
            .prefetch_related('request_video', 'request_transaction')

        filter_by_status = request.GET.get("status")
        if filter_by_status:
            if filter_by_status == 'all':
                filter_by_status = '2, 3, 4, 5, 6' if role == 'celebrity_id' else '2, 3, 1, 5, 6'
            try:
                filter_by_status = ast.literal_eval(filter_by_status+',')
            except Exception as e:
                return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_CODE', str(e))
            if role == 'fan_id' and STATUS_TYPES.completed in filter_by_status:
                user.completed_view_count = 0
                user.save()
            query_set = query_set.filter(request_status__in=filter_by_status)
        else:
            # Code block to be removed after the next sprint release
            result = {}
            for status in status_list:
                status = [status] if type(status) is not list else status
                all_requests = Stargramrequest.objects.filter(
                    Q(request_status__in=status) & Q(**custom_filter)
                ).select_related('occasion', 'fan', 'celebrity')\
                                   .prefetch_related('request_video', 'request_transaction')\
                                   .order_by('-created_date')[:5]
                result[STATUS_TYPES.get_label(status[0])] = self.get_serializer(all_requests, many=True).data
                if role == 'fan_id' and STATUS_TYPES.completed in status:
                    user.completed_view_count = 0
                    user.save()
            return self.jp_response('HTTP_200_OK', data=result)
            # Code block to be removed after the next sprint release
        query_set = query_set.order_by('-modified_date', 'celebrity__first_name')
        page = self.paginate_queryset(query_set.distinct())
        serializer = self.get_serializer(page, many=True)
        return self.paginator.get_paginated_response(serializer.data, key_name='request_list')


class OtherRelationship(APIView, ResponseViewMixin):

    def post(self, request):
        """
            Add other relations to occasion relationships
        """
        try:
            if 'other' in request.data:
                if type(request.data['other']) is str:
                    occasion = OccasionRelationship.objects.create(title=request.data['other'])
                    return self.jp_response(s_code='HTTP_200_OK', data={"id": occasion.id,
                                                                        "title": occasion.title})
            else:
                return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_CODE', 'Other Field is Required')
        except Exception as e:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'EXCEPTION',
                                          self.error_msg_string(str(e)))


class StargramzVideo(ViewSet, ResponseViewMixin):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)

    @detail_route(methods=['get'], permission_classes=[CustomPermission], authentication_classes=[])
    def get(self, request, pk):
        try:
            pk = hashids.decode(pk)[0]
        except Exception:
            pk = pk

        try:
            request_id = StargramVideo.objects.filter(id=pk).values('stragramz_request')
        except Exception:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_CODE', 'Video not found')

        try:
            video = StargramVideo.objects.filter(
                stragramz_request__request_status=STATUS_TYPES.completed,
                stragramz_request=request_id
            ).select_related('stragramz_request').prefetch_related(
                'stragramz_request__occasion',
                'stragramz_request__celebrity',
                'stragramz_request__celebrity__celebrity_profession__profession',
                'stragramz_request__celebrity__avatar_photo'
            ).order_by('-created_date')

            serializer = StargramzVideoSerializer(
                video, fields=[
                    'duration', 'full_name', 'celebrity_id', 's3_video_url', 's3_thumbnail_url', 'avatar_photo',
                    'professions', 'created_date', 'booking_title', 'video_url', 'width', 'height', 'booking_id',
                    'booking_type', 'video_status', 'comments_count', 'video_id', 'read_status'
                ],
                many=True
            )

            if serializer.data:
                return self.jp_response('HTTP_200_OK', data={'starsona_video': serializer.data})

        except Exception:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_CODE', 'Booking not completed')

        return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_CODE', 'Booking not completed')

    def create(self, request):
        """
            Create an Stargramz Video
        """
        try:
            booking = Stargramrequest.objects.get(id=request.data['stragramz_request'])
        except Stargramrequest.DoesNotExist:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_SIGNUP', 'Invalid Booking')

        try:
            user = StargramzUser.objects.get(username=request.user)
        except StargramzUser.DoesNotExist:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_SIGNUP', 'Invalid Signup User')

        serializer = StargramzVideoSerializer(
            data=request.data,
            fields=['stragramz_request', 'video', 'duration', 'thumbnail']
        )

        if serializer.is_valid():
            # Adding Video for Live Question by Fans.
            # check_user_role(user, ROLES.fan)
            if booking.request_status in [0, 1] and user.id == booking.fan_id and booking.request_type == REQUEST_TYPES.live_question_answer:
                editable = False
                try:
                    edit_time = Config.objects.get(key='booking_edit_time').value
                except Exception:
                    edit_time = REQUEST_EDIT_ALLOWED_TIME

                data = {}
                try:
                    if timezone.now() > booking.created_date + datetime.timedelta(minutes=int(edit_time)):
                        editable = False
                    else:
                        editable = True

                    if editable:
                        video = serializer.save(status=4, visibility=False)
                        generate_video_thumbnail.delay(id=video.id)
                        StargramVideo.objects.filter(stragramz_request_id=booking.id).exclude(id=video.id).delete()
                    else:
                        try:
                            video = StargramVideo.objects.get(stragramz_request=booking.id)
                        except Exception:
                            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_SIGNUP',
                                                          'Video cannot be added to bookings')

                    data = StargramzVideoSerializer(
                        video,
                        fields=['stragramz_request', 'video', 'duration', 'thumbnail']
                    ).data
                except StarsonaTransaction.DoesNotExist:
                    pass

                return self.jp_response('HTTP_200_OK', data={'request_video': data})

            # Starsona Request Video Creation
            try:
                stargramz_request = Stargramrequest.objects.get(
                    id=request.data['stragramz_request'],
                    celebrity_id=user.id,
                    request_status__in=[STATUS_TYPES.pending, STATUS_TYPES.processing]
                )
            except Stargramrequest.DoesNotExist:
                return self.jp_error_response(
                    'HTTP_400_BAD_REQUEST',
                    'INVALID_SIGNUP',
                    'Booking is not in processing state.'
                )
            # Payment capture process
            try:
                transaction = StarsonaTransaction.objects.get(starsona_id=stargramz_request.id)
                try:
                    charge = stripe.Charge.retrieve(transaction.stripe_transaction_id)
                except Exception as e:
                    self.transaction_update(transaction, TRANSACTION_STATUS.failed, str(e))
                    self.booking_update(stargramz_request, STATUS_TYPES.cancelled)
                    return self.jp_error_response(
                        'HTTP_400_BAD_REQUEST',
                        'INVALID_SIGNUP',
                        'Invalid transaction'
                    )

                # If the charge is not captured and not refunded
                if not charge.captured and not charge.refunded:
                    try:
                        charge.capture()
                        data = self.video_complete(serializer, stargramz_request, transaction)
                        return self.jp_response('HTTP_200_OK', data={'request_video': data})
                    except Exception as e:
                        self.booking_update(stargramz_request, STATUS_TYPES.cancelled)
                        self.transaction_update(transaction, TRANSACTION_STATUS.failed, str(e))
                        return self.jp_error_response(
                            'HTTP_400_BAD_REQUEST',
                            'INVALID_LOGIN',
                            data='Failed to process the Booking.'
                        )

                # If the charge is refunded
                elif charge.refunded:
                    self.booking_update(stargramz_request, STATUS_TYPES.cancelled)
                    self.transaction_update(transaction, TRANSACTION_STATUS.refunded, 'Amount has been refunded')
                    return self.jp_error_response(
                        'HTTP_400_BAD_REQUEST',
                        'INVALID_LOGIN',
                        data='Failed to process the Booking.'
                    )

                # If the charge is already captured
                elif charge.captured:
                    data = self.video_complete(serializer, stargramz_request, transaction)
                    return self.jp_response('HTTP_200_OK', data={'request_video': data})

            except Exception:
                self.booking_update(stargramz_request, STATUS_TYPES.cancelled)
                return self.jp_error_response(
                    'HTTP_400_BAD_REQUEST',
                    'INVALID_SIGNUP',
                    'Booking has no transaction history'
                )
        else:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_LOGIN',
                                          self.error_msg_string(serializer.errors))

    def transaction_update(self, transaction, status, comment, refund=None):
        """
            Update the Transactions
        """
        transaction.comments = comment
        transaction.transaction_status = status
        transaction.stripe_refund_id = refund
        transaction.save()

    def booking_update(self, booking, status):
        """
            Update the Bookings
        """
        booking.request_status = status
        booking.save()

    def video_complete(self, serializer, stargramz_request, transaction):
        """
            Save the video and sent email to admin to approve the video
        """
        video_status = 5 if stargramz_request.request_type == REQUEST_TYPES.live_question_answer else 1
        visible = False if video_status == 5 else True
        video_saved = serializer.save(status=video_status, visibility=visible)
        generate_video_thumbnail.delay(id=video_saved.id)
        if stargramz_request.request_type == REQUEST_TYPES.live_question_answer:
            combine_video_clips.delay(stargramz_request.id)
        self.booking_update(stargramz_request, STATUS_TYPES.video_approval)
        self.transaction_update(transaction, TRANSACTION_STATUS.captured, 'Successfully captured')
        data = StargramzVideoSerializer(video_saved, fields=[
            'stragramz_request', 'video', 'video_status', 'duration', 'thumbnail', 'comments_count'
        ]).data
        sender_email = Config.objects.get(key='sender_email').value
        admin_email = Config.objects.get(key='admin_email').value
        try:
            ctx = {
                'id': stargramz_request.id,
                'celebrity_name': stargramz_request.celebrity.get_short_name()
            }
            notify_email(sender_email, admin_email, SUBJECT_ADMIN_VIDEO_APPROVAL, 'video_approval', ctx)
        except Exception:
            pass
        return data


class FeaturedVideo(GenericViewSet, ResponseViewMixin):
    pagination_class = CustomOffsetPagination
    serializer_class = StargramzVideoSerializer

    def list(self, request):
        """
            List of Featured Videos
        """

        request_type = [1, 2, 3]
        req_type = request.GET.get('request_type', None)
        if req_type and int(req_type) in request_type:
            request_type = [int(req_type)]

        id = request.GET.get('id', None)

        if id:
            try:
                id = hashids.decode(id)[0]
            except Exception:
                id = id

            ordering = 'CASE WHEN "stargramz_stargramrequest"."id"=%s THEN 0 END' % id
            order_by = ('stragramz_request__id','-created_date')
        else:
            ordering = 'CASE WHEN "stargramz_stargramvideo"."status"= 1 THEN 1 END'
            order_by = ('-id', '-created_date')

        filter_by_related_id = request.GET.get('user_id', None)
        filter_by_name = request.GET.get('name', None)
        filter_by_date = request.GET.get('date', None)

        if filter_by_name:
            extra_select = None
        else:
            extra_select = {'stragramz_request__id': ordering}

        query_set = StargramVideo.objects.filter(
            stragramz_request__public_request=True,
            stragramz_request__request_status=STATUS_TYPES.completed,
            stragramz_request__request_type__in=request_type,
            status__in=[1, 2, 3],
        ).select_related('stragramz_request').prefetch_related(
            'stragramz_request__occasion',
            'stragramz_request__celebrity',
            'stragramz_request__fan',
            'stragramz_request__celebrity__celebrity_profession__profession',
            'stragramz_request__celebrity__avatar_photo',
            'stragramz_request__fan__avatar_photo',
            'stragramz_request__celebrity__vanity_urls'
        ).extra(select=extra_select, order_by=order_by)

        if filter_by_name:
            query_set = search_title_name(filter_by_name, query_set)

        today = datetime.datetime.now()

        if filter_by_date == 'today':
            query_set = query_set.filter(created_date=today)
        if filter_by_date == 'last_7_days':
            query_set = query_set.filter(created_date__gt=timezone.now()-datetime.timedelta(days=7))
        if filter_by_date == 'this_month':
            query_set = query_set.filter(created_date__gt=datetime.datetime(today.year, today.month, 1))
        if filter_by_date == 'this_year':
            query_set = query_set.filter(created_date__gt=datetime.datetime(today.year, 1, 1))

        # Filter celebrity videos for related video sections
        if filter_by_related_id:
            try:
                filter_by_related_id = VanityUrl.objects.values_list('user', flat=True).get(name=filter_by_related_id)
            except Exception:
                filter_by_related_id = filter_by_related_id
            query_set = query_set.filter(stragramz_request__celebrity=filter_by_related_id)

        page = self.paginate_queryset(query_set)
        serializer = self.get_serializer(
            page, fields=[
                'duration', 'full_name', 'booking_type', 'celebrity_id', 'booking_id', 'fan_avatar_photo', 'user_id',
                's3_video_url', 's3_thumbnail_url', 'avatar_photo', 'professions', 'created_date', 'booking_title',
                'video_url', 'width', 'height', 'question_answer_videos', 'following', 'occasion', 'fan_name',
                'comments_count', 'video_id', 'read_status'
            ],
            many=True
        )
        return self.paginator.get_paginated_response(serializer.data, key_name='featured_videos')


def search_title_name(filter_by_name, search_query):
    """
        Search celebrity name and title
    """

    query_set_list = []
    query_field_dict = {}
    for term in filter_by_name.split():
        query_set = search_query
        list_filter_fields = [
            'stragramz_request__celebrity__first_name',
            'stragramz_request__celebrity__last_name',
            'stragramz_request__celebrity__nick_name',
            'stragramz_request__booking_title'
        ]

        for list_field in list_filter_fields:
            kwargs = {list_field: None}
            query_field_dict[list_field] = list(set(query_set.values_list(list_field, flat=True).exclude(**kwargs)))

        for key, value in query_field_dict.items():
            close_matches = get_close_matches(term.lower(), value)
            kwargs_list_in = {str('%s__in' % key): close_matches}
            kwargs_contains = {str('%s__icontains' % key): term}
            querying = query_set.filter(Q(**kwargs_list_in) | Q(**kwargs_contains))
            if querying.exists():
                query_set_list.append(querying)

        if len(query_set_list) > 0:
            query_set = first = query_set_list[0]
            for postns in range(len(query_set_list) - 1):
                query_set = first = first | query_set_list[postns + 1]
        else:
            query_set = querying

    return query_set


class RequestReportAbuse(APIView, ResponseViewMixin):
    """
        Report Abuse against a Request by user
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission)

    def post(self, request):
        try:
            user = StargramzUser.objects.get(username=request.user)
        except Exception as e:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'EXCEPTION', self.error_msg_string(str(e)))

        try:
            Stargramrequest.objects.get(
                Q(id=request.data['request'])
                & (Q(celebrity_id=user.id) | Q(fan_id=user.id))
            )
        except Exception as e:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'EXCEPTION', 'Request not linked with the user')

        request.data['reported_by'] = user.id
        serializer = ReportAbuseSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return self.jp_response('HTTP_200_OK', data={'reported_abuse': "Added the request to Abuse list"})

        return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_LOGIN', self.error_msg_string(serializer.errors))


def play_video(request, id):
    """
        Web view for sharing and viewing videos of a request
    """
    data = {"base_url": BASE_URL}
    video_id = None

    try:
        video_id = hashids.decode(id)[0]
    except Exception as e:
        pass

    try:
        video = StargramVideo.objects.get(id=video_id)
        config = Config.objects.get(key='stargram_videos')
        celebrity = video.stragramz_request.celebrity.get_short_name()
        occasion = video.stragramz_request.occasion

        req_type = video.stragramz_request.request_type
        page_title = {
            1: "Watch this video shout-out from %s" % celebrity,
            2: "Check out my video announcement courtesy of %s" % celebrity,
            3: "%s answers my fan question!" % celebrity
        }
        page_desc = {
            1: "Get personalized videos from your favorite stars.",
            2: "Get personalized videos from your favorite stars.",
            3: "Get personalized videos from your favorite stars."
        }

        data = {
            "id": id,
            "video": get_pre_signed_get_url(video.video, config.value, 31536000),
            "image": get_s3_public_url(video.thumbnail, STARGRAM_VIDEO_THUMB),
            "url": "%s%s" % (BASE_URL, id),
            "celebrity": video.stragramz_request.celebrity.get_short_name(),
            "base_url": BASE_URL,
            "download_url": "/download/%s" % id,
            "title": "Starsona %s video from %s" % (occasion, celebrity),
            "page_title": page_title[req_type],
            "page_desc": page_desc[req_type],
            }

    except StargramVideo.DoesNotExist:
        pass

    return render(request=request, template_name='home/video.html', context=data)


def profile_detail(request, user_id):
    """
        Get the web view for Profile details
    """
    try:
        profile_id = VanityUrl.objects.values_list('user_id', flat=True).get(name=user_id)
    except Exception:
        pass

    data = {
        'description': 'Get your personlised video from your favorite celebrity',
        'image': '/media/web-images/star.png',
        'title': 'Starsona',
        'url': BASE_URL
    }

    try:
        profile = Celebrity.objects.values(
            'description',
            'user__first_name',
            'user__last_name',
            'user__nick_name',
            'user__avatar_photo'
        ).get(user_id=profile_id)

        picture = ProfileImage.objects.values('thumbnail').get(id=profile.get('user__avatar_photo'))

        config = Config.objects.get(key='profile_images')
        web_url = Config.objects.get(key='web_url').value
        try:
            vanity_url = VanityUrl.objects.values_list('name', flat=True).get(user_id=profile_id)
        except Exception:
            vanity_url = ''

        data = {
            "id": user_id,
            "description": "Book a personalized video shout-out from %s %s" %
                           (profile.get("user__first_name"), profile.get("user__last_name")),
            "image": get_s3_public_url(picture.get('thumbnail'), config.value),
            "url": "%sapplinks/profile/%s" % (BASE_URL, vanity_url),
            "title": "%s" % (profile.get("user__first_name")+' '+profile.get("user__last_name") if not profile.get("user__nick_name", None)
                             else profile.get("user__nick_name", None)),
            "weburl": "%s%s" % (web_url, vanity_url)
            }

    except Celebrity.DoesNotExist:
        pass

    return render(request=request, template_name='home/profile.html', context=data)


def request_detail(request, role, request_id):
    """
        Get the web view for Profile details
    """

    data = {
        'description': 'Get your personlised video from your favorite celebrity',
        'image': '%smedia/web-images/star.png' % BASE_URL,
        'title': 'Starsona',
        "url": "%sapplinks/request/%s/%s" % (BASE_URL, role, request_id),
        "id": request_id,
        "role": role,
    }

    return render(request=request, template_name='home/request.html', context=data)


def page_not_found(request):
    """
        404 page
    """
    return render(request=request, template_name='home/404.html', context={})


class CommentsView(GenericAPIView, ResponseViewMixin):
    """
        The list of celebrities and celebrity search
    """
    def get(self, request, pk):
        self.pagination_class = CustomOffsetPagination
        self.permission_classes = (CustomPermission,)

        try:
            video_id = hashids.decode(pk)[0]
        except Exception as e:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'EXCEPTION', str(e))
        try:
            kwargs = {'video_id': video_id, 'reply': None}
            try:
                comment_id = request.GET['last_comment'] if 'last_comment' in request.GET else None
                if comment_id and int(comment_id) > 0:
                    kwargs.update({'pk__lt': request.GET['last_comment']})
            except Exception:
                pass
            comment_details = Comment.objects.filter(**kwargs)
            comments = self.paginate_queryset(comment_details)
            serializer = CommentReplySerializer(comments, many=True)
            return self.paginator.get_paginated_response(serializer.data.__reversed__(), key_name='comment_list')
        except Exception as e:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'EXCEPTION', str(e))

    def post(self, request):

        self.authentication_classes = (TokenAuthentication,)
        self.permission_classes = (IsAuthenticated, CustomPermission,)
        self.pagination_class = CustomOffsetPagination

        try:
            user = StargramzUser.objects.get(username=request.user)
        except Exception as e:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'EXCEPTION', self.exception_response(str(e)))
        request.data['user'] = user.id
        serializer = CommentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return self.jp_response('HTTP_200_OK', data={"comments": "Added the comments"})
        else:
            return self.jp_response('HTTP_404_NOT_FOUND', data={"comments": serializer.errors})


class BookingFeedbackView(APIView, ResponseViewMixin):
    """
        Reaction video against a booking request video
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission)

    def post(self, request):

        try:
            user = StargramzUser.objects.get(username=request.user)
        except Exception as e:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'EXCEPTION', self.exception_response(str(e)))

        try:
            booking, celebrity = Stargramrequest.objects.values_list('id', 'celebrity').get(id=request.data.get('booking'))
        except Stargramrequest.DoesNotExist as e:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'EXCEPTION', self.exception_response(str(e)))

        request.data['user'] = user.id
        request.data['fan'] = user.id
        request.data['starsona'] = booking
        request.data['celebrity'] = celebrity
        rating = CelebrityRatingSerializer(data=request.data)
        reaction = ReactionSerializer(data=request.data)

        if reaction.is_valid() and rating.is_valid():
            reaction.save()
            fields = {
                'fan_rate': rating.validated_data.get('fan_rate'),
                'comments': rating.validated_data.get('comments', ''),
                'reason': rating.validated_data.get('reason', ''),
            }
            rating_record, created = FanRating.objects.update_or_create(
                fan_id=user.id, celebrity_id=celebrity, starsona_id=booking,
                defaults=fields)
            data = CelebrityRatingSerializer(rating_record).data
            return self.jp_response('HTTP_200_OK', data={"feedback": data})
        else:
            errors = reaction.errors if reaction.errors else rating.errors
            return self.jp_error_response(
                'HTTP_400_BAD_REQUEST',
                'INVALID_LOGIN',
                self.error_msg_string(errors)
            )


class RequesterWatchedVideo(APIView, ResponseViewMixin):
    """
        Video viewed by requested user
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission)

    def get(self, request, pk):
        try:
            video_id = hashids.decode(pk)[0]
        except Exception as e:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'EXCEPTION', str(e))

        try:
            user = StargramzUser.objects.get(username=request.user)
        except Exception as e:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'EXCEPTION', self.exception_response(str(e)))

        try:
            video = StargramVideo.objects.get(id=video_id, stragramz_request__fan=user.id, read_status=False)
            video.read_status = True
            video.save()
            return self.jp_response('HTTP_200_OK', data={"video_read": 'Updated the video'})
        except StargramVideo.DoesNotExist as e:
            return self.jp_response('HTTP_200_OK', data={"video_read": str(e)})


def get_bucket_private_url(request, id):
    """
    Create the s3 bucket url with valid
    :param request:
    :return:
    """
    try:
        video_id = hashids.decode(id)[0]
    except Exception:
        page_not_found(request)
    try:
        filename = StargramVideo.objects.values_list('video', flat=True).get(id=video_id)
    except Exception:
        page_not_found(request)
    try:
        url = get_pre_signed_get_url(filename, STARGRAM_VIDEOS)
    except Exception:
        page_not_found(request)
    return HttpResponsePermanentRedirect(url)
