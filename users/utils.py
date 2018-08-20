import random
import string


def generate_referral_unique_code(instance):
    """
        Generate the referral code for users
    """
    chars = string.digits
    name = ''.join(e for e in instance.get_short_name() if e.isalnum())[:5]
    code = name.upper()
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
    name = ''.join(e for e in get_full_name(instance) if e.isalpha())
    code = name.lower()
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
    return ' '.join(filter(None, [instance.first_name, instance.last_name]))
