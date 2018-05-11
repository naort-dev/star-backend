from django.db import models


class Config(models.Model):
    """
        Configurable details management
    """
    key = models.CharField('Key', max_length=100, blank=False, unique=True)
    value = models.CharField('Value', max_length=350, blank=True)
    status = models.BooleanField('Status', default=True)
    created_date = models.DateTimeField('Created Date', auto_now_add=True)
    modified_date = models.DateTimeField('Modified Date', auto_now=True)

    def __str__(self):
        return self.key

    class Meta:
        ordering = ['id']

    def save(self, *args, **kwargs):
        from config.tasks import build_config
        build_config.delay()
        super(Config, self).save(*args, **kwargs)