from django.contrib.sitemaps import Sitemap
from users.models import StargramzUser
from config.models import Config
from urllib.parse import urlparse
from django.db.models import Q


class VanityUrlSitemap(Sitemap):
    changefreq = 'daily'
    priority = 0.9

    def __init__(self):
        o = urlparse(Config.objects.get(key='web_url').value)
        self.domain = o.netloc
        self.protocol = o.scheme

    def get_urls(self, page=1, site=None, protocol=None):
        return self._urls(page, self.protocol, self.domain)

    def items(self):
        return StargramzUser.objects.select_related('vanity_urls').filter(
            Q(celebrity_user__admin_approval=True) & Q(vanity_urls__isnull=False))

    def lastmod(self, obj):
        return obj.vanity_urls.user.modified_date

    def location(self, obj):
        return '/' + obj.vanity_urls.name

