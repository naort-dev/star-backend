from django.db import models

from utilities.konstants import ROLES, FEATURES


class Feature(models.Model):
    code = models.CharField('Feature Code', max_length=5, unique=True)
    name = models.CharField('Name', max_length=128)

    def __str__(self):
        return '%s %s' % (self.code, self.name)

    def feature_display(self):
        return FEATURES.get_label(self.code)


class Role(models.Model):
    name = models.CharField('Name', max_length=128)
    code = models.CharField('Role Code', max_length=5, unique=True)
    features = models.ManyToManyField(Feature, related_name='features', through='RoleFeatureMapping')

    def __str__(self):
        return '%s %s' % (self.code, self.name)

    def role_display(self):
        return ROLES.get_label(self.code)


class RoleFeatureMapping(models.Model):
    role = models.ForeignKey(Role, on_delete=models.PROTECT)
    feature = models.ForeignKey(Feature, on_delete=models.PROTECT)
    privilege_enabled = models.BooleanField(default=True)

    class Meta:
        unique_together = ('role', 'feature')

    def __str__(self):
        return '%s %s' % (self.role, self.feature)
