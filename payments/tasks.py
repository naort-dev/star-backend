from main.celery import app
from .constants import NOTIFICATION_REQUEST_SUCCESS_TITLE, NOTIFICATION_REQUEST_SUCCESS_BODY
from utilities.konstants import NOTIFICATION_TYPES
from notification.tasks import send_notification
from stargramz.models import Stargramrequest, STATUS_TYPES
from users.models import StargramzUser, SettingsNotifications, Representative
from django.db.models import Q, F
from utilities.konstants import ROLES
from payments.models import TRANSACTION_STATUS, StarsonaTransaction, TipPayment, TIP_STATUS
import stripe
import json
from payments.constants import SECRET_KEY
from utilities.utils import check_user_role, encode_pk, generate_branch_io_url, sent_email
from job.tasks import send_sms, send_sms_celebrity
from utilities.constants import BASE_URL
from config.models import Config
import datetime


@app.task
def change_request_status_to_pending(request_id):
    """
        Change request status to pending
    """
    starsona = None
    try:
        starsona = Stargramrequest.objects.get(
            id=request_id,
            request_status=STATUS_TYPES.approval_pending
        )

        starsona.request_status = STATUS_TYPES.pending
        starsona.save()
        send_sms_notification(starsona)
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


def send_sms_notification(starsona):
    """
    Function will send notification SMS to the celebrity and his representatives informing about the new booking
    :param starsona:
    :return:
    """
    try:
        mob_link = 'request/?request_id=%s&role=R1002' % encode_pk(starsona.id)
        desktop_link = '%sapplinks/request/R1002/%s' % (BASE_URL, encode_pk(starsona.id))
        response_link = generate_branch_io_url(
            title="New Stasona Request",
            desc="New Stasona Request",
            mob_url=mob_link,
            desktop_url=desktop_link,
            image_url='%smedia/web-images/starsona_logo.png' % BASE_URL,
        )
        message = "Hi, You have a new booking in Starsona. Click here %s" % response_link
        send_sms_celebrity.delay(message, starsona.celebrity.id)
        message = "Hi, %s have a new booking. Please inform" % starsona.celebrity.get_short_name()
        representatives = Representative.objects.filter(celebrity=starsona.celebrity, sms_notify=True)
        for representative in representatives:
            country_code = representative.country_code[1:] if representative.country_code[0] == '+' else representative.country_code
            phone_number = "+%s%s" % (country_code, representative.phone)
            send_sms.delay(message, phone_number)
    except Exception:
        return False
    return True

@app.task
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


@app.task(name='tip_payments_payout')
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

                    tip_details.transaction_status = TIP_STATUS.tip_payed_out
                    tip_details.tip_payed_out = float(celebrity_tip_amount/100)
                    tip_details.payed_out_transaction_id = transfer.id
                    tip_details.payed_out_response = json.dumps(transfer)
                    tip_details.save()
                    tip_payment_celebrity_notification.delay(tip_details.id)
                    print('Successfully transferred amount to celebrity account')
                except Exception as e:
                    tip_details.transaction_status = TIP_STATUS.failed
                    tip_details.comments = str(e)
                    tip_details.save()
                    tip_payment_celebrity_notification.delay(tip_details.id)
                    print("Tip not payed: %s" % str(e))
            else:
                tip_details.transaction_status = TIP_STATUS.failed
                tip_details.comments = 'Insufficient balance. or stripe ID empty.'
                tip_details.save()
                tip_payment_celebrity_notification.delay(tip_details.id)
                print('Insufficient balance. or stripe user_id not linked.')
        except Exception as e:
            print("No TipPayment records: %s" % str(e))
    except Exception as e:
        print('Tip payment not valid. %s', str(e))


@app.task
def tip_payment_celebrity_notification(tip_id):
    try:
        tip_details = TipPayment.objects.get(id=tip_id)
        if tip_details.transaction_status == TIP_STATUS.tip_payed_out:
            template = "tip_payment_notification_payed_out"
            subject = "Tip has been transferred"
            ctx = {
                "celebrity_name": tip_details.celebrity.get_short_name(),
                "fan_name": tip_details.fan.get_short_name(),
                "tip_amount": tip_details.amount,
                "tip_amount_credited": tip_details.tip_payed_out,
                "booking_title": tip_details.booking.booking_title,
                "occasion": tip_details.booking.occasion.title
            }

        else:
            template = "tip_payment_notification_failed"
            subject = "Tip transfer failed"
            ctx = {
                "celebrity_name": tip_details.celebrity.get_short_name(),
                "fan_name": tip_details.fan.get_short_name(),
                "booking_title": tip_details.booking.booking_title,
            }
        to_email = tip_details.celebrity.email
        sent_email(to_email, subject, template, ctx)
        return True
    except Exception as e:
        print(str(e))
        return False


@app.task
def transaction_completed_notification(starsona_id):
    """
     The function will send transaction notification e-mail with details, to the fan
    :param starsona_id:
    :return:
    """
    try:
        web_url = Config.objects.get(key='web_url').value
        mob_link = 'request/?request_id=%s&role=R1001' % encode_pk(starsona_id)
        desktop_link = '%suser/myVideos' % web_url   # new desktop URL is needed
        date = datetime.datetime.now().strftime("%d/%m/%Y")
        booking = Stargramrequest.objects.get(id=starsona_id)
        transaction = StarsonaTransaction.objects.get(starsona=booking)
        to_email = booking.fan.email
        template = "transaction_status_to_fan"
        subject = "Starsona Transaction Status"
        ctx = {
            "fan_name": booking.fan.get_short_name(),
            "celebrity_name": booking.celebrity.get_short_name(),
            "occasion": booking.occasion.title,
            "booking_title": booking.booking_title,
            "date": date,
            "amount": str(transaction.amount),
            "app_url": generate_branch_io_url(
                title="New Stasona Request",
                desc="New Stasona Request",
                mob_url=mob_link,
                desktop_url=desktop_link,
                canonical_url="%srequest/R1001/%s" % (web_url, encode_pk(booking.id)),
                image_url='%smedia/web-images/starsona_logo.png' % BASE_URL
            )
        }
        sent_email(to_email, subject, template, ctx)
        return True
    except Exception:
        return False

@app.task
def credit_card_maintenance_notification(fan_id, attach):
    """
    The function will send the notification email to the fan informing about credit card addition or deletion
    :param fan_id:
    :param attach:
    :return:
    """
    try:
        fan = StargramzUser.objects.get(id=fan_id)
        to_email = fan.email
        template = "credit_card_notification"
        ctx = {"fan_name": fan.get_short_name()}
        if attach:
            subject = "Credit Card Added"
            ctx.update({"message": "A new credit card is added to your starsona account"})
        else:
            subject = "Credit Card Removed"
            ctx.update({"message": "The credit card is removed from your starsona account"})
        sent_email(to_email, subject, template, ctx)
        return True
    except Exception:
        return False
