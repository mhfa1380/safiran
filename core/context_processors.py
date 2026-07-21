"""
اطلاعات موسسه و تنظیمات سئو از دیتابیس و settings خوانده می‌شود.
"""

from django.conf import settings
from django.urls import reverse

from .cache_utils import get_institute_cached, get_site_navigation_cached
from .mhfa_live import get_central_footer_html
from .site_navigation import get_nav_countries_cached, has_active_courses_cached


def institute_info(request):
    """اضافه‌کردن شیء موسسه (کش‌شده) به context همه‌ی قالب‌ها."""
    return {"institute": get_institute_cached()}


def active_courses_info(request):
    """وجود یا عدم وجود دوره فعال برای نمایش شرطی لینک‌ها در قالب‌ها."""
    return {"has_active_courses": has_active_courses_cached()}


def nav_countries_info(request):
    """کشورهای مقصد فعال — سازگاری با قالب‌های قدیمی."""
    return {"nav_countries": get_nav_countries_cached()}


def site_navigation_info(request):
    """منو و فوتر متمرکز — نوبار، فوتر و لینک‌های مشترک."""
    institute = get_institute_cached()
    return {
        "site_nav": get_site_navigation_cached(getattr(institute, "name", "") or "")
    }


def mhfa_live_context(request):
    """Footer متمرکز MHFA Live — از کش سرور (بروزرسانی روزانه؛ خطای API صفحه را خراب نمی‌کند)."""
    if not getattr(settings, "MHFA_FOOTER_ENABLED", False):
        return {"mhfa_footer_html": ""}
    try:
        return {"mhfa_footer_html": get_central_footer_html()}
    except Exception:
        return {"mhfa_footer_html": ""}


def _normalize_external_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        return f"https://{url.lstrip('/')}"
    return url


def corner_promos_context(request):
    """پاپ‌آپ گوشه: ارزیابی چپ، کانال بله راست."""
    enabled = getattr(settings, "CORNER_PROMOS_ENABLED", True)
    bale_url = _normalize_external_url(getattr(settings, "BALE_CHANNEL_URL", ""))
    return {
        "corner_promos_enabled": enabled,
        "bale_channel_url": bale_url,
        "corner_promo_eval_url": reverse("evaluation") if enabled else "",
        "show_bale_corner_promo": enabled and bool(bale_url),
        "show_eval_corner_promo": enabled,
    }


def seo_context(request):
    """آدرس پایه سایت و متادیتای سئو برای قالب‌ها."""
    from .ai_discovery import build_organization_schema_context
    from .google_ai_seo import enrich_robots_for_google_ai
    from .seo_robots import resolve_meta_robots

    site_url = getattr(settings, "SITE_URL", "").rstrip("/")
    if not site_url and request:
        site_url = f"{request.scheme}://{request.get_host()}"
    canonical_url = f"{site_url}{request.path}" if (site_url and request) else (request.build_absolute_uri(request.path) if request else "")
    return {
        "site_url": site_url,
        "page_url": request.build_absolute_uri(request.path) if request else "",
        "canonical_url": canonical_url,
        "meta_robots": enrich_robots_for_google_ai(resolve_meta_robots(request)),
        **build_organization_schema_context(),
    }
