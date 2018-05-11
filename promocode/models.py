from django.db import models
from users.models import StargramzUser
from django.core.validators import MinValueValidator
from .constants import MIN_USER_VALUE

METRIC_TYPES = (
    ('fixed_amount', 'Fixed Amount'),
    ('percentage', 'Percentage'))


class Promocode(models.Model):
    name = models.CharField('Name', blank=False, max_length=100)
    code = models.CharField('Code', blank=False, max_length=100)
    valide_from = models.DateField('Valide from', blank=False)
    valide_to = models.DateField('Valide to', blank=True)
    specific_user = models.BooleanField('Specified users', default=False)
    promo_users = models.ManyToManyField(StargramzUser)
    users_per_coupon = models.IntegerField('Users per coupon', validators=[MinValueValidator(MIN_USER_VALUE)])
    uses_per_coupon = models.IntegerField('Uses per coupon', validators=[MinValueValidator(MIN_USER_VALUE)])
    type = models.CharField(max_length=15, choices=METRIC_TYPES, default='fixed_amount')
    discount = models.DecimalField(max_digits=9, decimal_places=2)
    status = models.BooleanField('Promocode Status', default=True)
    created_date = models.DateTimeField('Created date', auto_now_add=True, editable=False)
    modified_date = models.DateTimeField('Modified date', blank=True, null=True, editable=False)

