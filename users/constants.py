LINK_EXPIRY_DAY = 1
EMAIL_HOST_USER = 'support@stargramz.com'
CELEBRITY_CODE = 'R1003'
MIN_RATING_VALUE = 1.00
MAX_RATING_VALUE = 5.00
ROLE_ERROR_CODE = 310
EMAIL_ERROR_CODE = 410
FIRST_NAME_ERROR_CODE = 312
SORT = {'lpf': 'celebrity_user__rate',
        'hpf': '-celebrity_user__rate',
        'sr': '-celebrity_user__rating',
        'featured': 'order,-celebrity_user__view_count',
        'az': 'search_name',
        'za': '-search_name'
        }
OLD_PASSWORD_ERROR_CODE = 414
NEW_OLD_SAME_ERROR_CODE = 415
PROFILE_PHOTO_REMOVED = 'REMOVED'

# Alert Fan Notification
ALERT_FAN_NOTIFICATION_TITLE = 'Star is now available'
ALERT_FAN_NOTIFICATION_BODY = '%s is accepting booking requests. Book yours today!'

# Alert celebrity notification on account approval
NOTIFICATION_APPROVE_CELEBRITY_TITLE = 'Starsona'
NOTIFICATION_APPROVE_CELEBRITY_BODY = 'Your Starsona account has been approved.'
