from django.shortcuts import render
from rest_framework.views import APIView
from utilities.mixins import ResponseViewMixin
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from utilities.permissions import CustomPermission
from users.models import StargramzUser, Celebrity
from .serializer import EphemeralKeySerializer, ChargeSerializer, AttachDetachSourceSerializer, \
    StarsonaTransactionSerializer
import stripe
from .models import StarsonaTransaction, LogEvent, TRANSACTION_STATUS, PAYOUT_STATUS, StripeAccount, PaymentPayout
from stargramz.models import Stargramrequest, STATUS_TYPES
from config.models import Config
from django.db.models import Q
from .constants import TRANSACTION_PROCESSING_STATUS, PAID_TRANSACTIONS, PENDING_TRANSACTIONS, REDIRECT_URL, \
    CLIENT_ID, SECRET_KEY
import json
from rest_framework.viewsets import GenericViewSet
from utilities.pagination import CustomOffsetPagination
import uuid
import requests
from django.db.models import Sum
from .tasks import change_request_status_to_pending
from datetime import datetime, timedelta

API_KEY = SECRET_KEY
stripe.api_key = API_KEY


class GenerateEphemeralKey(APIView, ResponseViewMixin):

    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)

    def post(self, request):
        """
            Create Stripe customer if not exist and generate the EphemeralKey
        """
        stripe.api_key = API_KEY
        serializer = EphemeralKeySerializer(data=request.data)

        if serializer.is_valid():
            email = request.user
            api_version = serializer.validated_data.get('api_key')
            customer = StargramzUser.objects.get(username=request.user)

            if not customer.stripe_customer_id:
                customer.stripe_customer_id = self.createCustomer(email)
                customer.save()
            try:
                key = stripe.EphemeralKey.create(
                    customer=customer.stripe_customer_id,
                    api_version=api_version
                )
            except stripe.error.InvalidRequestError:
                customer.stripe_customer_id = self.createCustomer(email)
                customer.save()

                key = stripe.EphemeralKey.create(
                    customer=customer.stripe_customer_id,
                    api_version=api_version
                )
            except stripe.error.StripeError as e:
                return self.exception_response(data=str(e))
            return self.jp_response('HTTP_200_OK', data={"ephemeralKey": key})

        return self.jp_error_response(
            'HTTP_400_BAD_REQUEST',
            'UNKNOWN_QUERY',
            self.error_msg_string(serializer.errors)
        )

    def createCustomer(self, email):
        """
            Creates new stripe Customer
        """
        stripe.api_key = API_KEY

        try:
            customerDetails = stripe.Customer.create(
                description="Customer for "+str(email),
                email=email
            )
        except stripe.error.StripeError as e:
            return self.exception_response(data=str(e))

        return customerDetails.id


class CreateChargeFan(APIView, ResponseViewMixin):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)

    def post(self, request):
        """
            Create a Charge for a customer
        """
        customer = StargramzUser.objects.get(username=request.user)
        request.data['fan'] = customer.id
        serializer = ChargeSerializer(data=request.data)
        if serializer.is_valid():
            try:
                stargram_request = Stargramrequest.objects.get(Q(id=request.data['starsona']) &
                                                               Q(fan_id=request.data['fan']))
            except Stargramrequest.DoesNotExist:
                return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_UPDATE',
                                              'Request does not exist for this user')
            if not customer.stripe_customer_id:
                return self.jp_error_response('HTTP_400_BAD_REQUEST', 'UNKNOWN_QUERY',
                                              'Ephemeral key has not been generated')
            if str(stargram_request.celebrity.celebrity_user.rate) != str(request.data['amount']):
                return self.jp_error_response(
                    'HTTP_400_BAD_REQUEST', 'UNKNOWN_QUERY',
                    'The amount has been updated to %s' % stargram_request.celebrity.celebrity_user.rate)
            try:
                request_charge = stripe.Source.retrieve(request.data['source'], api_key=API_KEY)
            except Exception as e:
                return self.jp_error_response('HTTP_400_BAD_REQUEST', 'UNKNOWN_QUERY', str(e))
            transaction = StarsonaTransaction.objects.create(
                starsona_id=request.data['starsona'],
                fan_id=customer.id,
                celebrity_id=stargram_request.celebrity.id,
                amount=stargram_request.celebrity.celebrity_user.rate,
                transaction_status=TRANSACTION_STATUS.pending,
                source_id=request.data['source']
            )
            if request_charge.type == 'three_d_secure':
                if request_charge.status == 'failed':
                    transaction.transaction_status = TRANSACTION_STATUS.failed
                    transaction.save()
                    return self.jp_error_response('HTTP_400_BAD_REQUEST', 'UNKNOWN_QUERY',
                                                  'Payment has Failed')
                if request_charge.status != 'chargeable':
                    return self.jp_response(code_change=TRANSACTION_PROCESSING_STATUS,
                                            data={"charge_status": "Payment is under processing"})
            charge_id = createcharge(customer.stripe_customer_id,
                                     request.data['source'],
                                     request.data['starsona'],
                                     int(stargram_request.celebrity.celebrity_user.rate*100))

            if type(charge_id) is dict:
                transaction.delete()
                return self.exception_response(charge_id["Exception"])
            save_transaction_details(transaction, stargram_request, charge_id)
            try:
                edit_time = int(Config.objects.get(key='booking_edit_time').value)
            except Exception:
                edit_time = 15
            change_request_status_to_pending.apply_async((stargram_request.id,),
                                                         eta=datetime.utcnow() + timedelta(minutes=edit_time))
            return self.jp_response(data={"charge_status": "Payment was successful"})
        else:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'UNKNOWN_QUERY',
                                          self.error_msg_string(serializer.errors))


def createcharge(customer_id, source_id, starsona_id, amount):

    # Add card to stripe customer account
    try:
        cus_card = stripe.Customer.retrieve(customer_id, api_key=API_KEY)
        cus_card.source = source_id
        cus_card.save()
    except Exception as e:
        pass

    try:
        request_charge = stripe.Charge.create(
            amount=amount,
            currency='usd',
            customer=customer_id,
            description="Payment for the Starsona request " + str(starsona_id),
            metadata={"request_id": starsona_id},
            api_key=API_KEY,
            source=source_id,
            capture=False,
        )
        return request_charge.id
    except stripe.error.StripeError as e:
        return {"Exception": str(e)}


def save_transaction_details(transaction, stargram_request, charge_id):
    transaction.stripe_transaction_id = charge_id
    transaction.transaction_status = TRANSACTION_STATUS.authorized
    transaction.save()
    stargram_request.request_status = STATUS_TYPES.approval_pending
    stargram_request.save()


class EventLog(APIView, ResponseViewMixin):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        source_list = ['source.chargeable', 'source.failed', 'source.cancelled']
        log_event_data = LogEvent.objects.create(event=json.dumps(request.data), type=request.data['type'])
        loaded_event = json.loads(log_event_data.event)
        starsona_transaction = starsona_request = request_source = None
        try:
            request_source = stripe.Source.retrieve(loaded_event['data']['object']['id'], api_key=API_KEY)
        except Exception:
            pass
        if loaded_event['type'] in source_list and request_source:
            log_event_data.card_type = loaded_event['data']['object']['type']
            log_event_data.save()
            if loaded_event['data']['object']['type'] == 'three_d_secure':
                try:
                    starsona_transaction = StarsonaTransaction.objects.get(
                        source_id=loaded_event['data']['object']['id'])
                except StarsonaTransaction.DoesNotExist:
                    pass
                try:
                    starsona_request = Stargramrequest.objects.get(id=starsona_transaction.starsona_id)
                except Stargramrequest.DoesNotExist:
                    pass
                if starsona_transaction and starsona_request and request_source and \
                        not starsona_transaction.stripe_transaction_id:
                    if loaded_event['type'] == 'source.chargeable':
                        charge_id = createcharge(starsona_transaction.fan.stripe_customer_id,
                                                 starsona_transaction.source_id,
                                                 starsona_transaction.starsona_id,
                                                 int(starsona_transaction.amount*100))
                        if type(charge_id) is dict:
                            log_event_data.status_message = charge_id["Exception"]
                            log_event_data.save()
                            starsona_transaction.transaction_status = TRANSACTION_STATUS.failed
                            starsona_transaction.save()
                            return self.exception_response(charge_id["Exception"])
                        log_event_data.status_message = 'Charged'
                        log_event_data.save()
                        save_transaction_details(starsona_transaction, starsona_request, charge_id)
                        try:
                            edit_time = int(Config.objects.get(key='booking_edit_time').value)
                        except Exception:
                            edit_time = 15
                        change_request_status_to_pending.apply_async(
                            (starsona_request.id,),
                            eta=datetime.utcnow() + timedelta(minutes=edit_time)
                        )
                    elif request.data['type'] == 'source.failed':
                        log_event_data.status_message = 'Failed'
                        log_event_data.save()
                        starsona_transaction.transaction_status = TRANSACTION_STATUS.failed
                        starsona_transaction.save()
                    elif request.data['type'] == 'source.canceled':
                        log_event_data.status_message = 'Cancelled'
                        log_event_data.save()
                        starsona_transaction.transaction_status = TRANSACTION_STATUS.cancelled
                        starsona_transaction.save()
        return self.jp_response('HTTP_200_OK', "Event Logged Successfully")


class AttachDetachSource(APIView, ResponseViewMixin):
    """
        Attach and Detach Source to a customer
    """
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = AttachDetachSourceSerializer(data=request.data)
        if serializer.is_valid():
            try:
                cu = stripe.Customer.retrieve(request.data['customer'], api_key=API_KEY)
            except Exception as e:
                return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_LOGIN',
                                              str(e))
            if request.data['action']:
                try:
                    cu.sources.create(source={request.data['source']})
                    text = "attached"
                except Exception as e:
                    return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_LOGIN', str(e))
            else:
                try:
                    cu.sources.retrieve(request.data['source']).detach()
                    text = "detached"
                except Exception as e:
                    return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_LOGIN', str(e))
            cu.save()
            return self.jp_response('HTTP_200_OK', "Source %s Successfully" % text)
        else:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_LOGIN',
                                          self.error_msg_string(serializer.errors))


class CreateAccount(APIView, ResponseViewMixin):
    """
        Stripe account creation URL
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)

    def get(self, request):
        try:
            customer = StargramzUser.objects.get(username=request.user)
            uid = uuid.uuid4()
            StripeAccount.objects.create(id=uid, celebrity=customer)

            stripe_url = 'https://connect.stripe.com/express/oauth/authorize?redirect_uri=%s&client_id=%s&state=%s' % \
                         (REDIRECT_URL, CLIENT_ID, uid)

            return self.jp_response('HTTP_200_OK', data={'stripe_url': stripe_url})
        except Exception as e:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'EXCEPTION', str(e))


def stripe_connect(request):
    """
        Verify and create the stripe account for the user after the redirection from stripe website
    """
    if 'code' in request.GET and 'state' in request.GET:

        try:
            stripe_account = StripeAccount.objects.get(id=request.GET['state'], status=False)

            payload = {
                'client_secret': SECRET_KEY,
                'code': request.GET['code'],
                'grant_type': "authorization_code"
            }
            response = requests.post("https://connect.stripe.com/oauth/token", data=payload)

            response_data = response.json()
            stripe_account.response = response_data
            stripe_account.status = True
            stripe_account.save()

            if response.status_code == 200 and response_data['stripe_user_id']:

                account = stripe.Account.retrieve(response_data['stripe_user_id'])
                account.payout_schedule['interval'] = 'manual'
                account.save()

                try:
                    celebrity = Celebrity.objects.get(user=stripe_account.celebrity)
                    celebrity.stripe_user_id = response_data['stripe_user_id']
                    celebrity.save()
                except Celebrity.DoesNotExist:
                    pass

        except StripeAccount.DoesNotExist:
            pass

    return render(request=request, template_name='home/connect.html')


class EarningsList(GenericViewSet, ResponseViewMixin):

    """
        Get all the requests based on the status and provide the amounts paid/need to be paid to
        the Celebrity
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)
    pagination_class = CustomOffsetPagination
    serializer_class = StarsonaTransactionSerializer

    def list(self, request):
        user = StargramzUser.objects.get(username=request.user)
        try:
            Celebrity.objects.get(user_id=user.id)
        except Celebrity.DoesNotExist:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_LOGIN', 'Not an celebrity User')
        # Filter with the celebrity and request status which is complete
        celebrity_request_status_filter = {
            'celebrity_id': user.id,
            'starsona__request_status': STATUS_TYPES.completed,
            'transaction_payout__referral_payout': False
        }
        # Filter all completed transactions captured
        completed_custom_filter = {'transaction_status': TRANSACTION_STATUS.captured}
        # Filter the transactions with paid_out completed
        paid_custom_filter = {'transaction_payout__status__in': [PAYOUT_STATUS.transferred,
                                                                 PAYOUT_STATUS.check_transferred],
                              'transaction_payout__referral_payout': False
                              }
        query_set = StarsonaTransaction.objects.filter(**celebrity_request_status_filter)

        filter_by_status = request.GET.get("status")

        paid_starsonas = query_set.filter(**paid_custom_filter).order_by('-created_date')
        completed_starsonas = query_set.filter(**completed_custom_filter).order_by('-created_date')
        pending_starsonas = completed_starsonas.exclude(**paid_custom_filter)

        paid_starsonas_amount = paid_starsonas.aggregate(Sum('amount'))
        completed_stasonas_amount = completed_starsonas.aggregate(Sum('amount'))
        pending_starsonas_amount = pending_starsonas.aggregate(Sum('amount'))

        paid_amount = int(paid_starsonas_amount['amount__sum']) if paid_starsonas_amount['amount__sum'] else 0
        total_amount = int(completed_stasonas_amount['amount__sum']) if completed_stasonas_amount['amount__sum'] else 0
        pending_amount = int(pending_starsonas_amount['amount__sum']) if pending_starsonas_amount['amount__sum'] else 0

        # Referral amount
        users_amount = PaymentPayout.objects.filter(celebrity=user, referral_payout=True)\
            .aggregate(payed_out=Sum('fund_payed_out'))
        referral_payed_out = float(0 if not users_amount.get('payed_out', None) else users_amount.get('payed_out'))

        if filter_by_status:
            if filter_by_status == PENDING_TRANSACTIONS:
                query_set = pending_starsonas
            elif filter_by_status == PAID_TRANSACTIONS:
                query_set = paid_starsonas
        else:
            result = {}
            paid_stasonas_transactions = paid_starsonas[:5]
            result['Paid'] = self.get_serializer(paid_stasonas_transactions, many=True).data
            result['Paid_amount'] = paid_amount
            result['Total_amount'] = total_amount + referral_payed_out
            pending_starsonas_transactions = pending_starsonas[:5]
            result['Pending'] = self.get_serializer(pending_starsonas_transactions, many=True).data
            result['Pending_amount'] = pending_amount
            return self.jp_response('HTTP_200_OK', data=result)

        page = self.paginate_queryset(query_set.distinct())
        serializer = self.get_serializer(page, many=True)
        amounts = {'Paid_amount': paid_amount, 'Total_amount': total_amount, 'Pending_amount': pending_amount}
        return self.paginator.get_paginated_response(serializer.data, key_name='earning_list', amounts=amounts)


class StripeDashboard(APIView, ResponseViewMixin):
    """
        Generating the Stripe dashboard URL for user
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)

    def get(self, request):
        try:
            customer = Celebrity.objects.get(user__username=request.user)
            if customer.stripe_user_id:
                account = stripe.Account.retrieve(customer.stripe_user_id)
                acc_details = account.external_accounts.data[0]
                card_details = '%s xxxx-%s' % (acc_details.brand, acc_details.last4) if acc_details.object == 'card' \
                    else '%s xxxx-%s' % (acc_details.bank_name, acc_details.last4)
                stripe_details = account.login_links.create()
            else:
                return self.jp_error_response('HTTP_400_BAD_REQUEST', 'EXCEPTION', "Stripe not configured")

            return self.jp_response('HTTP_200_OK', data={
                'stripe_details': stripe_details,
                'card_details': card_details
            })
        except Exception as e:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'EXCEPTION', str(e))


class CardsList(APIView, ResponseViewMixin):
    """
        Get the card list added to a customer in stripe
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)

    def get(self, request):
        try:
            customer = StargramzUser.objects.get(username=request.user)
            try:
                if customer.stripe_customer_id:
                    account = stripe.Customer.retrieve(customer.stripe_customer_id, api_key=API_KEY)
                    card_details = account.sources.data
                    cards = {}
                    for i, card in card_details:
                        cards[i] = {'id': card.id, 'last4': card.last4}

                    return self.jp_response('HTTP_200_OK', data={'cards': cards})
                else:
                    return self.jp_error_response('HTTP_400_BAD_REQUEST', 'EXCEPTION', 'Not a stripe customer')
            except Exception as e:
                return self.jp_error_response('HTTP_400_BAD_REQUEST', 'EXCEPTION', str(e))
        except Exception as e:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'EXCEPTION', str(e))
