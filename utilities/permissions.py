from config.models import Config
from rest_framework import status
from rest_framework.exceptions import APIException, _get_error_details
from rest_framework.permissions import BasePermission
from .constants import ANDROID, ANDROID_CONFIG_KEY, IOS, IOS_CONFIG_KEY, WEB
from config.constants import *
from django.utils.translation import ugettext_lazy as _
from django.utils import six
from distutils.version import StrictVersion
import json

def error_function(status_code, message=None):
    return {
        "status": status_code,
        "error": {
            "message": message,
            "code": status_code
        }
    }


class CustomValidationError(APIException):
    default_status_code = status.HTTP_409_CONFLICT
    default_detail = _('Invalid input.')
    default_code = 'invalid'

    def __init__(self, detail, code=None, status_code=None):
        if detail is None:
            detail = self.default_detail
        if code is None:
            code = self.default_code
        self.status_code = status_code if status_code is not None else self.default_status_code
        if not isinstance(detail, dict) and not isinstance(detail, list):
            detail = [detail]

        self.detail = _get_error_details(detail, code)

    def __str__(self):
        return six.text_type(self.detail)


class CustomPermission(BasePermission):
    """
    Global permission for checking versions
    """
    def has_permission(self, request, view):
        try:
            config = json.loads(open('config/versions.json').read())
            android_version = config['android_version']
            ios_version = config['ios_version']
        except Exception:
            android_version = ANDROID_VERSION
            ios_version = IOS_VERSION

        if 'HTTP_DEVICE' in request.META and request.META['HTTP_DEVICE'].lower() == WEB:
            return True

        if 'HTTP_VERSION' in request.META and 'HTTP_DEVICE' in request.META:
            if request.META['HTTP_DEVICE'].lower() == ANDROID:
                config = android_version
                try:
                    if StrictVersion(config) > StrictVersion(request.META['HTTP_VERSION']):
                        raise ValueError("Version is not compatible")
                    else:
                        return True
                except Exception as e:
                    raise CustomValidationError(detail=error_function(409, str(e)),
                                                status_code=status.HTTP_409_CONFLICT)
            elif request.META['HTTP_DEVICE'].lower() == IOS:
                config = ios_version
                try:
                    if StrictVersion(config) > StrictVersion(request.META['HTTP_VERSION']):
                        raise ValueError("Version is not compatible")
                    else:
                        return True
                except Exception as e:
                    raise CustomValidationError(detail=error_function(409, str(e)),
                                                status_code=status.HTTP_409_CONFLICT)
            else:
                raise CustomValidationError(
                    detail=error_function(409, "Device Type is not of available choices"),
                    status_code=status.HTTP_409_CONFLICT)

        else:
            raise CustomValidationError(
                detail=error_function(409, "Version and Device Type are not provided"),
                status_code=status.HTTP_409_CONFLICT)
