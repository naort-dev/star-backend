from django.shortcuts import render
from rest_framework.views import APIView
from utilities.mixins import ResponseViewMixin
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from utilities.permissions import CustomPermission
from users.models import StargramzUser, Celebrity
from .serializer import EphemeralKeySerializer, ChargeSerializer, AttachDetachSourceSerializer, \
    StarsonaTransactionSerializer, TipPaymentSerializer, BookingValidate, CreditCardNotificationSerializer, \
    InAppSerializer
import stripe
from .models import StarsonaTransaction, LogEvent, TRANSACTION_STATUS, PAYOUT_STATUS, StripeAccount, PaymentPayout,\
    TipPayment, TIP_STATUS, PAYMENT_TYPES
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
from .tasks import change_request_status_to_pending, tip_payments_payout, transaction_completed_notification,\
    credit_card_maintenance_notification
from datetime import datetime, timedelta
from config.constants import *
from utilities.utils import decode_pk
from .utils import has_ambassador
from job.tasks import verify_referee_discount
from utilities.authentication import CustomAuthentication

API_KEY = SECRET_KEY
stripe.api_key = API_KEY


class GenerateEphemeralKey(APIView, ResponseViewMixin):

    authentication_classes = (CustomAuthentication,)
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
                    stripe_version=api_version
                )
            except stripe.error.InvalidRequestError:
                customer.stripe_customer_id = self.createCustomer(email)
                customer.save()

                key = stripe.EphemeralKey.create(
                    customer=customer.stripe_customer_id,
                    stripe_version=api_version
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
    authentication_classes = (CustomAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)

    def post(self, request):
        """
            Create a Charge for a customer
        """
        customer = StargramzUser.objects.get(username=request.user)
        request.data['fan'] = customer.id
        try:
            request.data['starsona'] = decode_pk(request.data['starsona'])
        except:
            pass
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
                return self.stripe_exception_response(str(e))
            actual_amount = stargram_request.celebrity.celebrity_user.rate
            ambassador_amount = 0.0
            if has_ambassador(stargram_request.celebrity.id):
                ambassador_amount = round((float(actual_amount) * (20.0 / 100.0)), 2)
                actual_amount = round((float(actual_amount) * (60.0 / 100.0)), 2)
            else:
                referee_discount = verify_referee_discount(stargram_request.celebrity.id)
                actual_amount = round((float(actual_amount) * (referee_discount / 100.0)), 2)
            transaction = StarsonaTransaction.objects.create(
                starsona_id=request.data['starsona'],
                fan_id=customer.id,
                celebrity_id=stargram_request.celebrity.id,
                amount=stargram_request.celebrity.celebrity_user.rate,
                actual_amount = actual_amount,
                ambassador_amount = ambassador_amount,
                transaction_status=TRANSACTION_STATUS.pending,
                source_id=request.data['source']
            )
            if has_ambassador(stargram_request.celebrity.id):
                ambassador_transaction = StarsonaTransaction.objects.create(
                    starsona_id=request.data['starsona'],
                    fan_id=customer.id,
                    celebrity_id=stargram_request.celebrity.ambassador.id,
                    amount=ambassador_amount,
                    actual_amount=ambassador_amount,
                    ambassador_amount=0.0,
                    transaction_status=TRANSACTION_STATUS.captured,
                    source_id=request.data['source'],
                    ambassador_transaction=True
                )
            if request_charge.type == 'three_d_secure':
                if request_charge.status == 'failed':
                    transaction.transaction_status = TRANSACTION_STATUS.failed
                    ambassador_transaction.transaction_status = TRANSACTION_STATUS.failed
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
                ambassador_transaction.delete()
                return self.stripe_exception_response(charge_id["Exception"])
            save_transaction_details(transaction, stargram_request, charge_id)
            transaction_completed_notification.delay(stargram_request.id)
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
        return {"Exception": ':Card is not chargeable, Please try with another card'}


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
                        source_id=loaded_event['data']['object']['id'], ambassador_transaction=False)
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
                    cu.sources.create(source=request.data['source'])
                    text = "attached"
                    credit_card_maintenance_notification.delay(request.user.id, True)
                except Exception as e:
                    return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_LOGIN', str(e))
            else:
                try:
                    cu.sources.retrieve(request.data['source']).detach()
                    text = "detached"
                    credit_card_maintenance_notification.delay(request.user.id, False)
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
    authentication_classes = (CustomAuthentication,)
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
                    user = StargramzUser.objects.get(id=stripe_account.celebrity_id)
                    user.stripe_user_id = response_data['stripe_user_id']
                    user.save()
                except Celebrity.DoesNotExist:
                    pass

        except StripeAccount.DoesNotExist:
            pass

    try:
        web_url = Config.objects.get(key='web_url').value
    except Exception:
        web_url = BASE_URL

    data = {'web_url': web_url}
    return render(request=request, template_name='home/connect.html', context=data)


class EarningsList(GenericViewSet, ResponseViewMixin):

    """
        Get all the requests based on the status and provide the amounts paid/need to be paid to
        the Celebrity
    """
    authentication_classes = (CustomAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)
    pagination_class = CustomOffsetPagination
    serializer_class = StarsonaTransactionSerializer

    def list(self, request):
        from job.tasks import verify_referee_discount
        user = StargramzUser.objects.get(username=request.user)
        try:
            Celebrity.objects.get(user_id=user.id)
        except Celebrity.DoesNotExist:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_LOGIN', 'Not an celebrity User')
        # Filter with the celebrity and request status which is complete
        celebrity_request_status_filter = {
            'celebrity_id': user.id,
            'starsona__request_status': STATUS_TYPES.completed,
        }
        # Filter all completed transactions captured
        completed_custom_filter = {'transaction_status': TRANSACTION_STATUS.captured}
        # Filter the transactions with paid_out completed
        paid_custom_filter = {'transaction_payout__status__in': [PAYOUT_STATUS.transferred,
                                                                 PAYOUT_STATUS.check_transferred],
                              'transaction_payout__referral_payout': False
                              }
        pending_custom_filter = {
            'transaction_payout__status__in': [
                PAYOUT_STATUS.transferred,
                PAYOUT_STATUS.check_transferred
            ]
        }
        query_set = StarsonaTransaction.objects.filter(**celebrity_request_status_filter)\
            .prefetch_related('transaction_payout', 'starsona__fan', 'starsona__occasion',)\
            .select_related('starsona',)

        all_results = query_set.order_by('-created_date')

        filter_by_status = request.GET.get("status")

        paid_starsonas = query_set.filter(**paid_custom_filter).order_by('-created_date')
        completed_starsonas = query_set.filter(**completed_custom_filter).order_by('-created_date')
        pending_starsonas = completed_starsonas.exclude(**pending_custom_filter)

        paid_starsonas_amount = paid_starsonas.aggregate(Sum('actual_amount'))
        completed_stasonas_amount = completed_starsonas.aggregate(Sum('actual_amount'))
        pending_starsonas_amount = pending_starsonas.aggregate(Sum('actual_amount'))


        paid_amount = float(paid_starsonas_amount['actual_amount__sum']) if paid_starsonas_amount['actual_amount__sum'] else 0
        total_amount = float(completed_stasonas_amount['actual_amount__sum']) if completed_stasonas_amount['actual_amount__sum'] else 0
        pending_amount = float(pending_starsonas_amount['actual_amount__sum']) if pending_starsonas_amount['actual_amount__sum'] else 0


        # Referral amount
        users_amount = PaymentPayout.objects.filter(celebrity=user, referral_payout=True)\
            .aggregate(payed_out=Sum('fund_payed_out'))
        referral_payed_out = float(0 if not users_amount.get('payed_out', None) else users_amount.get('payed_out'))

        ambassador_transaction = StarsonaTransaction.objects.filter(celebrity__ambassador=user, transaction_status=TRANSACTION_STATUS.captured)
        ambassador_amount = 0.0
        if ambassador_transaction:
            ambassador_amount = ambassador_transaction.aggregate(ambassador_amount=Sum('ambassador_amount'))
            ambassador_amount = float(0 if not ambassador_amount.get('ambassador_amount', None) else ambassador_amount.get('ambassador_amount'))

        if filter_by_status:
            if filter_by_status == PENDING_TRANSACTIONS:
                query_set = pending_starsonas
            elif filter_by_status == PAID_TRANSACTIONS:
                query_set = paid_starsonas
            elif filter_by_status == 'all':
                query_set = all_results
        else:
            result = {}
            paid_stasonas_transactions = paid_starsonas[:5]
            result['Paid'] = self.get_serializer(paid_stasonas_transactions, many=True).data
            result['Paid_amount'] = round(paid_amount, 2)
            result['referral_payed_out'] = round(referral_payed_out, 2)
            result['Total_amount'] = round(total_amount + referral_payed_out + ambassador_amount, 2)
            pending_starsonas_transactions = pending_starsonas[:5]
            result['Pending'] = self.get_serializer(pending_starsonas_transactions, many=True).data
            result['Pending_amount'] = round(pending_amount, 2)
            return self.jp_response('HTTP_200_OK', data=result)

        page = self.paginate_queryset(query_set.distinct())
        serializer = self.get_serializer(page, many=True)
        amounts = {
            'Paid_amount': round(paid_amount, 2),
            'Total_amount': round(total_amount + referral_payed_out + ambassador_amount, 2),
            'referral_payed_out': round(referral_payed_out, 2),
            'Pending_amount': round(pending_amount, 2)
        }
        return self.paginator.get_paginated_response(serializer.data, key_name='earning_list', amounts=amounts)


class StripeDashboard(APIView, ResponseViewMixin):
    """
        Generating the Stripe dashboard URL for user
    """
    authentication_classes = (CustomAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)

    def get(self, request):
        try:
            customer = StargramzUser.objects.get(username=request.user)
            if customer.stripe_user_id:
                account = stripe.Account.retrieve(customer.stripe_user_id)
                acc_details = account.external_accounts.data[0]
                card_details = '%s xxxx-%s' % (acc_details.brand, acc_details.last4) if acc_details.object == 'card' \
                    else '%s xxxx-%s' % (acc_details.bank_name, acc_details.last4)
                stripe_details = account.login_links.create()
            else:
                return self.jp_response('HTTP_200_OK', data={'message': "Stripe not configured"})

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
    authentication_classes = (CustomAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)

    def get(self, request):
        try:
            customer = StargramzUser.objects.get(username=request.user)
            try:
                if customer.stripe_customer_id:
                    account = stripe.Customer.retrieve(customer.stripe_customer_id, api_key=API_KEY)
                    card_details = account.sources.data
                    cards = {}
                    for i, card in enumerate(card_details):
                        if card['type'] == 'card' and 'card' in card:
                            cards[i] = {
                                'id': card['id'],
                                'last4': card['card']['last4'],
                                'brand': card['card']['brand']
                            }
                    return self.jp_response('HTTP_200_OK', data={'cards': cards})
                else:
                    return self.jp_error_response('HTTP_400_BAD_REQUEST', 'EXCEPTION', 'Not a stripe customer')
            except Exception as e:
                return self.jp_error_response('HTTP_400_BAD_REQUEST', 'EXCEPTION', str(e))
        except Exception as e:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'EXCEPTION', str(e))


class TipPayments(APIView, ResponseViewMixin):
    authentication_classes = (CustomAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)

    def query_check(self, request, customer):
        booking, celebrity = Stargramrequest.objects.values_list('id', 'celebrity').get(
            Q(id=request.data['booking']) &
            Q(fan_id=customer.id))
        return booking, celebrity

    def post(self, request):
        """
            Create a Charge for a customer
        """
        try:
            customer = StargramzUser.objects.get(username=request.user)
        except Exception as e:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'UNKNOWN_QUERY', str(e))
        request.data['fan'] = customer.id

        try:
            request.data['booking'] = decode_pk(request.data['booking'])
        except Exception:
            pass

        serializer = BookingValidate(data=request.data)
        if serializer.is_valid():
            try:
                booking, celebrity = self.query_check(request, customer)
            except Stargramrequest.DoesNotExist:
                return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_UPDATE',
                                              'Request does not exist for this user')
            if not customer.stripe_customer_id:
                return self.jp_error_response(
                    'HTTP_400_BAD_REQUEST',
                    'UNKNOWN_QUERY',
                    'Ephemeral key has not been generated'
                )
            request.data['celebrity'] = celebrity
            tips = TipPaymentSerializer(data=request.data)
            if tips.is_valid():
                try:
                    request_charge = stripe.Source.retrieve(request.data['source'], api_key=API_KEY)
                except Exception as e:
                    return self.jp_error_response('HTTP_400_BAD_REQUEST', 'UNKNOWN_QUERY',
                                                  'Card is not chargeable, try with another card.')
                tip_transaction = TipPayment.objects.create(
                    booking_id=booking,
                    fan_id=customer.id,
                    celebrity_id=celebrity,
                    amount=tips.validated_data.get('amount'),
                    transaction_status=TIP_STATUS.pending,
                    source_id=tips.validated_data.get('source'),
                )
                if request_charge.type == 'three_d_secure':
                    if request_charge.status == 'failed':
                        tip_transaction.transaction_status = TIP_STATUS.failed
                        tip_transaction.save()
                        return self.jp_error_response('HTTP_400_BAD_REQUEST', 'UNKNOWN_QUERY',
                                                      'Payment has Failed')
                    if request_charge.status != 'chargeable':
                        return self.jp_response(code_change=TRANSACTION_PROCESSING_STATUS,
                                                data={"charge_status": "Payment is under processing"})

                try:
                    charge = stripe.Charge.create(
                        amount=int(tips.validated_data.get('amount')*100),
                        currency='usd',
                        customer=customer.stripe_customer_id,
                        description="Tip for the Starsona request " + str(booking),
                        metadata={"request_id": booking},
                        api_key=API_KEY,
                        source=tips.validated_data.get('source'),
                        capture=True,
                    )
                    tip_transaction.stripe_transaction_id = charge.id
                    tip_transaction.transaction_status = TIP_STATUS.captured
                    tip_transaction.save()
                    # Transfer tip amount to celbrity account
                    tip_payments_payout.delay(tip_transaction.id)
                    return self.jp_response(data={"tip_status": "Tip payment was successful"})
                except Exception as e:
                    tip_transaction.transaction_status = TIP_STATUS.failed
                    tip_transaction.comments = str(e)
                    tip_transaction.save()
                    return self.jp_error_response('HTTP_400_BAD_REQUEST', 'UNKNOWN_QUERY',
                                                  'Card is not chargeable, Try with another card.')


            else:
                return self.jp_error_response('HTTP_400_BAD_REQUEST', 'UNKNOWN_QUERY', tips.errors)
        else:
            return self.jp_error_response(
                'HTTP_400_BAD_REQUEST',
                'UNKNOWN_QUERY',
                self.error_msg_string(serializer.errors)
            )


class CreditCardNotification(APIView, ResponseViewMixin):
    authentication_classes = (CustomAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)

    def get(self, request):
        try:
            user = StargramzUser.objects.get(id=request.user.id)
        except Exception as e:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'UNKNOWN_QUERY', str(e))

        serializer = CreditCardNotificationSerializer(data=request.GET)
        if serializer.is_valid():
            attach = serializer.validated_data.get('attach')
            credit_card_maintenance_notification.delay(user.id, attach)

            return self.jp_response(data={"message": "Notification sent Successfully"})
        else:
            return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_LOGIN',
                                          self.error_msg_string(serializer.erros))


class InAppPurchase(APIView, ResponseViewMixin):
    authentication_classes = (CustomAuthentication,)
    permission_classes = (IsAuthenticated, CustomPermission,)

    def post(self, request):
        """
            In-App purchase for IOS users
        """
        request.data['fan'] = request.user.id
        request.data['stripe_transaction_id'] = request.data['transaction_id']
        serializer = InAppSerializer(data=request.data)
        if serializer.is_valid():
            try:
                stargram_request = Stargramrequest.objects.get(
                    Q(id=serializer.validated_data.get('starsona')) & Q(fan_id=serializer.validated_data.get('fan'))
                )
            except Stargramrequest.DoesNotExist:
                return self.jp_error_response('HTTP_400_BAD_REQUEST', 'INVALID_UPDATE',
                                              'Request does not exist for this user')
            actual_amount = round((float(request.data['amount']) * (70.0/100.0)), 2)
            ambassador_amount = 0.0
            if has_ambassador(stargram_request.celebrity.id):
                ambassador_amount = round((float(actual_amount) * (20.0 / 100.0)), 2)
                actual_amount = round((float(actual_amount) * (60.0 / 100.0)), 2)
            else:
                referee_discount = verify_referee_discount(stargram_request.celebrity.id)
                actual_amount = round((float(actual_amount) * (referee_discount / 100.0)), 2)
            StarsonaTransaction.objects.create(
                starsona_id=serializer.validated_data.get('starsona', ''),
                fan_id=serializer.validated_data.get('fan'),
                celebrity_id=stargram_request.celebrity.id,
                amount=float(request.data['amount']),
                actual_amount=actual_amount,
                ambassador_amount=ambassador_amount,
                transaction_status=TRANSACTION_STATUS.captured,
                source_id='in_app',
                stripe_transaction_id=serializer.validated_data.get('stripe_transaction_id'),
                payment_type=PAYMENT_TYPES.in_app
            )
            if has_ambassador(stargram_request.celebrity.id):
                ambassador_transaction = StarsonaTransaction.objects.create(
                    starsona_id=serializer.validated_data.get('starsona', ''),
                    fan_id=serializer.validated_data.get('fan'),
                    celebrity_id=stargram_request.celebrity.ambassador.id,
                    amount=ambassador_amount,
                    actual_amount=ambassador_amount,
                    ambassador_amount=0.0,
                    transaction_status=TRANSACTION_STATUS.captured,
                    source_id='in_app',
                    stripe_transaction_id=serializer.validated_data.get('stripe_transaction_id'),
                    payment_type=PAYMENT_TYPES.in_app,
                    ambassador_transaction=True
                )
            stargram_request.request_status = STATUS_TYPES.approval_pending
            stargram_request.save()
            transaction_completed_notification.delay(stargram_request.id)
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
