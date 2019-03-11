from rest_framework import status
from rest_framework.response import Response

from utilities.konstants import K, Konstants

ERROR_CODE = Konstants(
    K(EXCEPTION=1001, label='Exception'),
    K(INVALID_SIGNUP=1002, label='Invalid signup'),
    K(INVALID_USER=1003, label='Invalid user details supplied'),
    K(INVALID_LOGIN=1004, label='Invalid login'),
    K(USER_EXISTS=1005, label='User Already exists'),
    K(INVALID_CODE=1006, label='Invalid code supplied'),
    K(INVALID_CREATE=1007, label='Invalid creation'),
    K(INVALID_UPDATE=1008, label='Invalid update'),
    K(UNKNOWN_QUERY=1009, label='Unknown object')
)


class ResponseViewMixin(object):
    ignore_keys = ['non_field_errors', ]

    def jp_response(self, s_code='HTTP_200_OK', data=None, code_change=None):
        code_changes = code_change if code_change else getattr(status, s_code)
        return Response(status=getattr(status, s_code),
                        data={'status': code_changes,
                              'data': data,
                              'success': True},
                        content_type='application/json'
                        )

    def jp_error_response(self, s_code='HTTP_500_INTERNAL_SERVER_ERROR', e_code='EXCEPTION',
                          data=None, code_change=None):
        if type(data) is str:
            data = data
        code_changes = code_change if code_change else str(getattr(status, s_code))
        return Response(status=getattr(status, s_code),
                        data={'status': code_changes,
                              'error': {'code': getattr(ERROR_CODE, e_code),
                                        'message': data}},
                        content_type='application/json'
                        )

    def stripe_exception_response(self, data=None):
        """
        Filter out the unwanted parts of the exception message
        :param data:
        :return:
        """
        msg = data
        if data:
            data = data.split(':')
            if len(data) > 2:
                msg = data[1]
        return self.jp_error_response('HTTP_400_BAD_REQUEST', 'UNKNOWN_QUERY', msg)

    def exception_response(self, data=None):
        return self.jp_error_response('HTTP_500_INTERNAL_SERVER_ERROR', 'EXCEPTION', data)

    def error_msg_list(self, errors):
        errors_list = []
        for k, v in errors.items():
            if isinstance(v, dict):
                v = self.error_msg_list(v)
            for msg in v:
                if k in self.ignore_keys:
                    errors_list.append(msg)
                else:
                    errors_list.append(' '.join(k.title().split('_')) + '- ' + str(msg))
        return errors_list

    def error_msg_string(self, errors):
        errors_string = ''
        for k, v in errors.items():
            if isinstance(v, dict):
                v = self.error_msg_list(v)
            for msg in v:
                msg = msg.replace("']", "")
                msg = msg.replace("['", "")
                errors_string = ''.join(str(msg))
        return errors_string

    def error_dict(self, errors):
        errors_list = dict()
        for k, v in errors.items():
            if isinstance(v, dict):
                v = self.error_msg_list(v)
            for msg in v:
                errors_list[k] = msg
        return errors_list

    def response_key_value_pair(self, data):
        response_list = dict()
        for key in data:
            response_list[key['key']] = key['value']
        return response_list
