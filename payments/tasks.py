from main.celery import app
from .constants import NOTIFICATION_REQUEST_SUCCESS_TITLE, NOTIFICATION_REQUEST_SUCCESS_BODY
from utilities.konstants import NOTIFICATION_TYPES
from notification.tasks import send_notification
from stargramz.models import Stargramrequest, STATUS_TYPES
from users.models import StargramzUser
from django.db.models import Q, F
from utilities.konstants import ROLES
from payments.models import TRANSACTION_STATUS, StarsonaTransaction, TipPayment, TIP_STATUS
import stripe
import json
from payments.constants import SECRET_KEY
from utilities.utils import check_user_role


@app.task
def change_request_status_to_pending(request_id):
    """
        Change request status to pending
    """
    starsona = None
    try:
        starsona = Stargramrequest.objects.get(
            id=request_id,
            request_status=STATUS_TYPES.approval_pending,
            request_transaction__transaction_status__in=[2, 3]
        )

        starsona.request_status = STATUS_TYPES.pending
        starsona.save()
        pending_request_count = Stargramrequest.objects.filter(
            request_status=STATUS_TYPES.pending,
            celebrity=starsona.celebrity.id
        ).count()
        unseen_bookings = 0
        try:
            user = StargramzUser.objects.get(id=starsona.celebrity.id)
            unseen_bookings = user.unseen_bookings + 1
            user.unseen_bookings = F('unseen_bookings') + 1
            user.save()
        except Exception:
            pass

        data = {'id': starsona.id, 'type': NOTIFICATION_TYPES.celebrity_booking_open_details,
                'pending_request_count': pending_request_count, 'role': ROLES.celebrity,
                'unseen_bookings': unseen_bookings}
        send_notification.delay(starsona.celebrity.id,
                                NOTIFICATION_REQUEST_SUCCESS_TITLE,
                                NOTIFICATION_REQUEST_SUCCESS_BODY,
                                data, field='celebrity_starsona_request')
    except Stargramrequest.DoesNotExist:
        print('Booking doesnt exist with payment completed.')
        return True


@app.task(bind=True, max_retries=0)
def create_request_refund():
    starsona = None
    print('Transaction Task')
    requests = Stargramrequest.objects.filter(request_status=STATUS_TYPES.cancelled)\
        .exclude(request_transaction__transaction_status=TRANSACTION_STATUS.refunded)
    for request in requests:
        try:
            starsona = StarsonaTransaction.objects.get(starsona_id=request.id)
        except StarsonaTransaction.DoesNotExist:
            pass
        if starsona:
            stripe.api_key = SECRET_KEY
            if starsona.stripe_transaction_id:
                print("Starsona Transaction " + str(starsona.stripe_transaction_id))
                try:
                    starsona_charge = stripe.Charge.retrieve(starsona.stripe_transaction_id)
                    if starsona_charge.refunded:
                        try:
                            refund_id = starsona_charge.refunds.data[0]['id']
                        except Exception:
                            refund_id = ''

                    if not starsona_charge['refunded']:
                        refund_charge = stripe.Refund.create(charge=starsona_charge.id).id
                        try:
                            starsona.stripe_refund_id = refund_charge
                            starsona.transaction_status = TRANSACTION_STATUS.refunded
                            starsona.save()
                            print("The request refunded is %s" % starsona_charge.id,
                                  "The Refund id is %s" % refund_charge)
                        except stripe.error.StripeError as e:
                            print(str(e))
                    else:
                        starsona.stripe_refund_id = refund_id
                        starsona.transaction_status = TRANSACTION_STATUS.refunded
                        starsona.save()
                except stripe.error.StripeError as e:
                    print(str(e))


@app.task(bind=True, max_retries=0, name='tip_payments_payout')
def tip_payments_payout(tip_id):
    """
    Send tip payments to celebrity accounts
    :param tip_id:
    :return:
    """
    stripe.api_key = SECRET_KEY
    try:
        tip_details = TipPayment.objects.get(pk=tip_id, transaction_status=2)
        try:
            payout_amount = stripe.Charge.retrieve(tip_details.stripe_transaction_id, expand=['balance_transaction'])
            celebrity_tip_amount = payout_amount.balance_transaction.net

            balance = stripe.Balance.retrieve()
            available_balance = balance.available[0]['amount']
            print("Total amount in Balance: %d" % int(available_balance))

            if available_balance > celebrity_tip_amount and tip_details.celebrity.stripe_user_id:
                try:
                    transfer = stripe.Transfer.create(
                        amount=celebrity_tip_amount,
                        currency="usd",
                        destination=tip_details.celebrity.stripe_user_id,
                        description="Tip payment for booking %d" % int(tip_details.booking_id)
                    )

                    tip_details.status = TIP_STATUS.tip_payed_out
                    tip_details.tip_payed_out = float(celebrity_tip_amount/100)
                    tip_details.payed_out_transaction_id = transfer.id
                    tip_details.payed_out_response = json.dumps(transfer)
                    tip_details.save()
                    print('Successfully transferred amount to celebrity account')
                except Exception as e:
                    print("Tip not payed: %s" % str(e))
            else:
                print('Insufficient balance. or stripe ID empty.')

        except Exception as e:
            print("No TipPayment records: %s" % str(e))
    except Exception as e:
        print('Tip payment not valid. %s', str(e))
