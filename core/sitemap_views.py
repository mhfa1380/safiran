"""
View سفارشی sitemap با هدر کش مناسب برای خزنده‌ها.
"""
from django.contrib.sitemaps.views import sitemap as django_sitemap

_CACHE_CONTROL = "public, max-age=900, must-revalidate"


def sitemap_view(request, sitemaps=None, **kwargs):
    response = django_sitemap(request, sitemaps=sitemaps, **kwargs)
    response["Cache-Control"] = _CACHE_CONTROL
    response["X-Robots-Tag"] = "noindex"
    return response
