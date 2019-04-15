from django.db import models


class CelebrityDisplayOrganizer(models.Model):
    title = models.CharField(max_length=120, null=True, blank=True)
    profession = models.ForeignKey('users.Profession', related_name='profession_celebrity', null=True, blank=True, on_delete=models.CASCADE)

    def __str__(self):
        if self.profession and self.profession.title:
            return self.profession.title
        elif self.title:
            return self.title
        else:
            return "Display organizer"


class CelebrityDisplay(models.Model):
    celebrity = models.ForeignKey('users.StargramzUser', related_name='celebrity_display', blank=True, null=True, on_delete=models.CASCADE)
    order = models.IntegerField('celebrity order', blank=True, null=True)
    celebrity_display = models.ForeignKey(CelebrityDisplayOrganizer, related_name='celebrity_display_organizer', null=True,
                                          blank=True, on_delete=models.CASCADE)
