"""
اطلاعات موسسه و تنظیمات سئو از دیتابیس و settings خوانده می‌شود.
"""

from types import SimpleNamespace

from django.conf import settings
from django.core.cache import cache

from .models import Institute


_INSTITUTE_CACHE_KEY = "core_institute_singleton"
_INSTITUTE_CACHE_TIMEOUT = 300  # ۵ دقیقه


def get_institute_cached():
    """خواندن اطلاعات موسسه با کش سبک برای جلوگیری از کوئری تکراری در هر ریکوئست."""
    institute = cache.get(_INSTITUTE_CACHE_KEY)
    if institute is not None:
        return institute

    obj = Institute.objects.first()
    if obj is None:
        obj = SimpleNamespace(
            name="موسسه",
            province="",
            city="",
            phone="",
            phone_formatted="",
            email="",
            address="",
            website="",
            website_url="",
            license_issue_date="",
            license_expiry_date="",
            type_title="",
            students_sent=0,
            countries_count=0,
        )

    cache.set(_INSTITUTE_CACHE_KEY, obj, _INSTITUTE_CACHE_TIMEOUT)
    return obj


def institute_info(request):
    """اضافه‌کردن شیء موسسه (کش‌شده) به context همه‌ی قالب‌ها."""
    return {"institute": get_institute_cached()}


def seo_context(request):
    """آدرس پایه سایت و متادیتای سئو برای قالب‌ها."""
    site_url = getattr(settings, "SITE_URL", "").rstrip("/")
    if not site_url and request:
        site_url = f"{request.scheme}://{request.get_host()}"
    # canonical و og:url همیشه به آدرس واقعی سایت اشاره کنند (حتی در لوکال)
    canonical_url = f"{site_url}{request.path}" if (site_url and request) else (request.build_absolute_uri(request.path) if request else "")
    return {
        "site_url": site_url,
        "page_url": request.build_absolute_uri(request.path) if request else "",
        "canonical_url": canonical_url,
    }
