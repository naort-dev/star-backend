from django.db import models


class New(models.Model):
    title = models.CharField('Title', blank=False, max_length=256)
    description = models.TextField('Description', blank=False)
    image = models.FileField(upload_to='news/', blank=True, null=True)
    created_date = models.DateTimeField('Created date', auto_now_add=True, editable=False)

    def __str__(self):
        return self.title
