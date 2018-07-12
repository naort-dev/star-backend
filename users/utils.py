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
