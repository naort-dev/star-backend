import os

TRANSACTION_PROCESSING_STATUS = "225"
REDIRECT_URL = os.environ.get('STRIPE_WEB_HOOK')
CLIENT_ID = os.environ.get('STRIPE_CLIENT_ID')
SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
PENDING_TRANSACTIONS = "1"
PAID_TRANSACTIONS = "2"

# Notification Constants
NOTIFICATION_REQUEST_SUCCESS_TITLE = 'New starsona booking'
NOTIFICATION_REQUEST_SUCCESS_BODY = 'Fan has requested a personalized video from you'
