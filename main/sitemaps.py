from django.contrib.sitemaps import Sitemap
from users.models import StargramzUser
from config.models import Config
from urllib.parse import urlparse
from django.template.response import TemplateResponse
from django.urls import reverse
from django.db.models import Q


def index(request, sitemaps,
          template_name='sitemap_index.xml', content_type='application/xml',
          sitemap_url_name='django.contrib.sitemaps.views.sitemap'):

    o = urlparse(Config.objects.get(key='web_url').value)
    domain = o.netloc
    protocol = o.scheme

    sites = []
    for section, site in sitemaps.items():
        if callable(site):
            site = site()
        sitemap_url = reverse(sitemap_url_name, kwargs={'section': section})
        sitemap_file = sitemap_url.split('/')[-1]
        absolute_url = '%s://%s/%s' % (protocol, domain, sitemap_file)
        sites.append(absolute_url)
        for page in range(2, site.paginator.num_pages + 1):
            sites.append('%s?p=%s' % (absolute_url, page))

    return TemplateResponse(request, template_name, {'sitemaps': sites},
                            content_type=content_type)

class VanityUrlSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.9

    def __init__(self):
        o = urlparse(Config.objects.get(key='web_url').value)
        self.domain = o.netloc
        self.protocol = o.scheme

    def get_urls(self, page=1, site=None, protocol=None):
        return self._urls(page, self.protocol, self.domain)

    def items(self):
        return StargramzUser.objects.select_related('vanity_urls').values('modified_date', 'vanity_urls__name').filter(
            Q(celebrity_user__admin_approval=True) & Q(vanity_urls__isnull=False))

    def lastmod(self, obj):
        return obj['modified_date']

    def location(self, obj):
        return '/' + obj['vanity_urls__name']

