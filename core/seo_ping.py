"""
اعلام به‌روزرسانی sitemap به موتورهای جستجو پس از تغییر محتوا.

با debounce کوتاه از درخواست‌های پشت‌سرهم جلوگیری می‌شود.
"""
from __future__ import annotations

import logging
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

_PING_ENDPOINTS = (
    "https://www.bing.com/ping",
)
_CACHE_KEY = "seo:sitemap_ping_debounce"
_DEBOUNCE_SECONDS = 120


def ping_search_engines_sitemap() -> None:
    """Ping Google/Bing با آدرس sitemap (در صورت فعال بودن در تنظیمات)."""
    if not getattr(settings, "SEO_SITEMAP_PING_ENABLED", True):
        return

    site_url = (getattr(settings, "SITE_URL", None) or "").strip().rstrip("/")
    if not site_url:
        return

    if cache.get(_CACHE_KEY):
        return
    cache.set(_CACHE_KEY, 1, _DEBOUNCE_SECONDS)

    sitemap_url = f"{site_url}/sitemap.xml"
    query = urllib.parse.urlencode({"sitemap": sitemap_url})

    for base in _PING_ENDPOINTS:
        url = f"{base}?{query}"
        try:
            req = urllib.request.Request(url, method="GET", headers={"User-Agent": "SafiranSitemapPing/1.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                logger.info("Sitemap ping OK %s status=%s", base, resp.status)
        except urllib.error.HTTPError as exc:
            logger.warning("Sitemap ping HTTP error %s: %s", base, exc)
        except Exception as exc:
            logger.warning("Sitemap ping failed %s: %s", base, exc)
