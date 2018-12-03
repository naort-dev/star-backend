import random
import string
import re
from django.db.models import Q


def generate_referral_unique_code(instance):
    """
        Generate the referral code for users
    """
    chars = string.digits
    name = re.sub('[^A-Za-z0-9]+', '', instance.get_short_name())
    if len(name) == 0:
        name = re.sub('[^A-Za-z0-9]+', '', get_vanity_from_email(instance))
    code = name.upper()[:5]
    size = 8 - len(code)
    referral_code = ''.join(random.choice(chars) for _ in range(size))
    code = str(code) + (referral_code[:8])

    users = instance.__class__

    if users.objects.filter(referral_code=code).exists():
        return generate_referral_unique_code(instance)
    return code


def generate_random_code(size=2):
    """
        Generate a random code
    """
    chars = string.ascii_uppercase+string.digits
    return ''.join(random.choice(chars) for _ in range(size))


def generate_vanity_url(instance, value_exist=0):
    """
    Create vanity URL from the users name
    :param instance: Users model instance
    :param value_exist: integer auto increment value
    :return: vanity url name
    """
    from users.models import VanityUrl

    name = re.sub('[^A-Za-z0-9]+', '', get_full_name(instance))
    code = name.lower()
    if len(code) == 0:
        code = re.sub('[^A-Za-z0-9]+', '', get_vanity_from_email(instance))
    if value_exist > 0 or len(code) == 0:
        chars = string.digits
        random_code = ''.join(random.choice(chars) for _ in range(value_exist))
        code = str(code) + '-' + random_code

    if VanityUrl.objects.filter(name=code).exists():
        return generate_vanity_url(instance, value_exist+1)
    return code


def get_full_name(instance):
    """
    Get the full name of a user from model
    :param instance: Users instance
    :return: full name
    """
    if instance.show_nick_name and instance.nick_name:
        return instance.nick_name
    return ''.join(filter(None, [instance.first_name, instance.last_name]))


def get_vanity_from_email(instance):
    """
    Get the vanity name from email
    :param instance:
    :return: email name
    """
    email = instance.email
    return email.split("@")[0]


def search_name(filter_by_name, search_query, filter_fields):
    """
    Update the search query to add the search filters in the filter fields
    Query will filter data according to the filter name in each filter_fields
    :param filter_by_name:
    :param search_query:
    :param filter_fields:
    :return: result_query with name filter
    """
    query_set_list = []
    query_field_dict = {}

    ######
    filter_by_name = filter_by_name.lower()

    for term in filter_by_name.split():
        q_objects = Q()
        for key in filter_fields:
            kwargs_contains = {str('%s__icontains' % key): term}
            q_objects |= Q(**kwargs_contains)

        querying = search_query.filter(q_objects).distinct()
        if querying.exists():
            query_set_list.append(querying)
            query_set = first = query_set_list[0]
            for index in range(len(query_set_list) - 1):
                query_set = first | query_set_list[index + 1]
        else:
            query_set = querying

    ######
    # for term in filter_by_name.split():
    #     query_set = search_query
    #     list_filter_fields = ['first_name', 'last_name', 'nick_name', 'celebrity_user__description',
    #                           'celebrity_user__charity']
    #     profession_filters = ['celebrity_profession__profession__title',
    #                           'celebrity_profession__profession__parent__title']
    #     for list_field in list_filter_fields:
    #         kwargs = {list_field: None}
    #         query_field_dict[list_field] = list(set(query_set.values_list(list_field, flat=True).exclude(**kwargs)))
    #
    #     for key, value in query_field_dict.items():
    #         close_matches = get_close_matches(term.lower(), value)
    #         kwargs_list_in = {str('%s__in' % key): close_matches}
    #         kwargs_contains = {str('%s__icontains' % key): term}
    #         querying = query_set.filter(Q(**kwargs_list_in) | Q(**kwargs_contains))
    #         if querying.exists():
    #             query_set_list.append(querying)
    #     for profession_filter in profession_filters:
    #         kwargs = {str('%s__icontains' % profession_filter): term}
    #         querying = query_set.filter(**kwargs)
    #         if querying.exists():
    #             query_set_list.append(querying)
    #     if len(query_set_list) > 0:
    #         query_set = first = query_set_list[0]
    #         for postns in range(len(query_set_list) - 1):
    #             query_set = first = first | query_set_list[postns + 1]
    #     else:
    #         query_set = querying
    return query_set
