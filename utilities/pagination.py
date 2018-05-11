from rest_framework.pagination import PageNumberPagination, LimitOffsetPagination
from utilities.mixins import ResponseViewMixin


class CustomPagesizePagination(PageNumberPagination):
    page_size = 2
    page_size_query_param = 'page_size'
    page_query_param = 'page'
    max_page_size = 1000


class CustomOffsetPagination(LimitOffsetPagination, ResponseViewMixin):
    default_limit = 10
    limit_query_param = 'limit'
    offset_query_param = 'offset'
    max_limit = 100

    def get_paginated_response(self, data, **kwargs):
        key = kwargs.pop('key_name', 'details')
        amounts = kwargs.pop('amounts', None)
        data = {
                key: data,
                'links': {
                   'next': self.next_offset(),
                   'previous': self.previous_offset()
                }, 'count': self.count,
            }
        if amounts:
            for key, value in amounts.items():
                data[key] = value
        return self.jp_response(s_code='HTTP_200_OK', data=data)

    def next_offset(self):
        if self.offset + self.limit >= self.count:
            return None
        offset = self.offset + self.limit
        return offset

    def previous_offset(self):
        if self.offset <= 0:
            return None
        offset = self.offset - self.limit
        return offset
