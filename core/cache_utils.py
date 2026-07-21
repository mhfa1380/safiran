"""
کش مشترک — تعادل سرعت و تازگی داده (باطل‌سازی فوری پس از ویرایش ادمین).
"""

from __future__ import annotations

from functools import wraps
from types import SimpleNamespace
from typing import Any, Callable

from django.conf import settings
from django.core.cache import cache
from django.views.decorators.cache import cache_page

INSTITUTE_CACHE_KEY = "core_institute_singleton"
NAV_COUNTRIES_CACHE_KEY = "core_nav_study_countries"
HAS_ACTIVE_COURSES_CACHE_KEY = "core_has_active_courses"
HAS_ACTIVE_COURSES_EXISTS_KEY = "core_has_active_courses_exists"
PUBLIC_STATS_CACHE_KEY = "core:public_stats:v1"
SITE_NAV_VERSION_KEY = "core:site_nav:ver"
CONTENT_CACHE_VERSION_KEY = "core:content:ver"
SEARCH_CACHE_VERSION_KEY = "core:search:ver"
SERVICE_CATEGORIES_CACHE_KEY = "core:service_categories:v1"
PRICING_PAGE_CACHE_KEY = "core:pricing_page:v2"
BLOG_TAGS_CACHE_KEY = "blog_tags:v2"
BLOG_SEARCH_VERSION_KEY = "blog_search:ver"
EVAL_CATALOG_CACHE_PREFIX = "core:eval_catalog"

_HTML_VIEW_CACHE: dict[tuple, Callable] = {}


def _seconds(name: str, default: int) -> int:
    return int(getattr(settings, name, default))


def page_cache_enabled() -> bool:
    if settings.DEBUG and not getattr(settings, "PAGE_CACHE_IN_DEBUG", False):
        return False
    return page_cache_seconds() > 0


def api_cache_seconds() -> int:
    return _seconds("API_CACHE_SECONDS", 45)


def browse_api_cache_seconds() -> int:
    return _seconds("BROWSE_API_CACHE_SECONDS", 180)


def content_cache_version() -> int:
    return int(cache.get(CONTENT_CACHE_VERSION_KEY) or 1)


def search_cache_version() -> int:
    return int(cache.get(SEARCH_CACHE_VERSION_KEY) or 1)


def evaluation_catalog_cache_key() -> str:
    """کش کاتالوگ موتور ارزیابی — با نسخه محتوا باطل می‌شود."""
    return f"{EVAL_CATALOG_CACHE_PREFIX}:c{content_cache_version()}"


def blog_api_cache_key(namespace: str, *parts: str) -> str:
    """کلید کش API وبلاگ — با نسخه محتوا پس از ویرایش پست."""
    ver = cache.get(BLOG_SEARCH_VERSION_KEY) or 1
    return api_cache_key(f"{namespace}:v{ver}", *parts)


def api_cache_key(namespace: str, *parts: str) -> str:
    """کلید AJAX — با باطل‌سازی هنگام ویرایش محتوا."""
    safe = ":".join((p or "").replace(":", "_") for p in parts)
    return f"{namespace}:s{search_cache_version()}:c{content_cache_version()}:{safe}"


def get_api_cached(key: str) -> Any:
    if not key:
        return None
    return cache.get(key)


def set_api_cached(key: str, data: Any, *, timeout: int | None = None) -> None:
    if not key:
        return
    cache.set(key, data, timeout if timeout is not None else api_cache_seconds())


def set_browse_api_cached(key: str, data: Any) -> None:
    """کش طولانی‌تر برای لیست/فیلتر بدون جستجو."""
    set_api_cached(key, data, timeout=browse_api_cache_seconds())


def get_institute_cached():
    institute = cache.get(INSTITUTE_CACHE_KEY)
    if institute is not None:
        return institute

    from .models import Institute

    obj = Institute.objects.first()
    if obj is None:
        obj = SimpleNamespace(
            name="موسسه",
            province="",
            city="",
            phone="",
            phone_formatted="",
            mobile="",
            mobile_formatted="",
            primary_call_number="",
            primary_call_formatted="",
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

    cache.set(INSTITUTE_CACHE_KEY, obj, _seconds("INSTITUTE_CACHE_SECONDS", 300))
    return obj


def get_public_stats_cached() -> dict[str, int]:
    stats = cache.get(PUBLIC_STATS_CACHE_KEY)
    if stats is not None:
        return stats

    from .models import ConsultationSlot, University

    booked_slots = ConsultationSlot.objects.filter(is_booked=True).count()
    stats = {
        "university_count": University.objects.count(),
        "consultation_hours": int(round(booked_slots * 0.5)),
    }
    cache.set(PUBLIC_STATS_CACHE_KEY, stats, _seconds("PUBLIC_STATS_CACHE_SECONDS", 90))
    return stats


def has_active_courses_exists_cached() -> bool:
    flag = cache.get(HAS_ACTIVE_COURSES_EXISTS_KEY)
    if flag is not None:
        return bool(flag)

    from .models import Course

    flag = Course.objects.filter(is_active=True).exists()
    cache.set(HAS_ACTIVE_COURSES_EXISTS_KEY, flag, _seconds("SITE_NAV_CACHE_SECONDS", 300))
    return flag


def get_service_categories_cached() -> list:
    categories = cache.get(SERVICE_CATEGORIES_CACHE_KEY)
    if categories is not None:
        return categories

    from .models import ServiceCategory

    categories = list(
        ServiceCategory.objects.filter(is_active=True)
        .only(
            "id",
            "name",
            "slug",
            "description",
            "icon",
            "meta_title",
            "meta_description",
            "order",
            "is_active",
        )
        .order_by("order", "id")
    )
    cache.set(
        SERVICE_CATEGORIES_CACHE_KEY,
        categories,
        _seconds("SITE_NAV_CACHE_SECONDS", 300),
    )
    return categories


def _site_nav_cache_key(institute_name: str) -> str:
    version = cache.get(SITE_NAV_VERSION_KEY, 1)
    safe_name = (institute_name or "default")[:80]
    return f"core:site_nav:v{version}:{safe_name}"


def get_site_navigation_cached(institute_name: str = "") -> dict[str, Any]:
    key = _site_nav_cache_key(institute_name)
    nav = cache.get(key)
    if nav is not None:
        return nav

    from .site_navigation import build_site_navigation

    nav = build_site_navigation(institute_name)
    cache.set(key, nav, _seconds("SITE_NAV_CACHE_SECONDS", 300))
    return nav


def invalidate_search_caches() -> None:
    try:
        cache.incr(SEARCH_CACHE_VERSION_KEY)
    except ValueError:
        cache.set(SEARCH_CACHE_VERSION_KEY, 2, None)


def invalidate_content_html_caches() -> None:
    """باطل‌سازی فوری HTML کش‌شده — پس از publish در ادمین."""
    try:
        cache.incr(CONTENT_CACHE_VERSION_KEY)
    except ValueError:
        cache.set(CONTENT_CACHE_VERSION_KEY, 2, None)
    _HTML_VIEW_CACHE.clear()


def get_pricing_page_data_cached() -> dict[str, Any]:
    data = cache.get(PRICING_PAGE_CACHE_KEY)
    if data is not None:
        return data

    from django.db.models import Prefetch

    from .models import LivingAllowanceCountry, PricingCategory, PricingTariff, StudyCountry
    from .pricing_countries import build_study_countries_pricing

    categories = list(
        PricingCategory.objects.filter(is_active=True).prefetch_related(
            Prefetch(
                "tariffs",
                queryset=PricingTariff.objects.filter(is_active=True).order_by("order", "id"),
            )
        )
    )
    tariffs_flat = list(
        PricingTariff.objects.filter(is_active=True).select_related("category")
    )
    study_countries = list(
        StudyCountry.objects.filter(is_active=True)
        .select_related("allowance_country")
        .order_by("order", "id")
    )
    allowance_all = list(LivingAllowanceCountry.objects.filter(is_active=True))
    study_pricing = build_study_countries_pricing(
        study_countries=study_countries,
        tariffs=tariffs_flat,
        allowance_countries=allowance_all,
    )
    countries = [
        c
        for c in allowance_all
        if c.slug
        in {sc["allowance_slug"] for sc in study_pricing["countries"] if sc.get("allowance_slug")}
    ]
    countries_json = [
        {
            "slug": c.slug,
            "name": c.name,
            "amount": c.amount,
            "currency": c.currency,
            "display": c.allowance_display,
            "region": c.region_group,
            "search": f"{c.name} {c.search_keywords} {c.region_group}".lower(),
        }
        for c in countries
    ]
    study_allowance_slugs = {
        sc["allowance_slug"] for sc in study_pricing["countries"] if sc.get("allowance_slug")
    }
    allowance_rows = [
        {
            "name": c["name"],
            "display": c["display"],
            "region": c.get("region", ""),
            "slug": c["slug"],
        }
        for c in countries_json
        if c["slug"] in study_allowance_slugs
    ]

    data = {
        "categories": categories,
        "tariffs": tariffs_flat,
        "countries_json": countries_json,
        "allowance_rows": allowance_rows,
        "study_countries": study_countries,
        "study_pricing": study_pricing,
        "study_pricing_json": study_pricing,
    }
    cache.set(PRICING_PAGE_CACHE_KEY, data, _seconds("PRICING_CACHE_SECONDS", 120))
    return data


def invalidate_layout_caches() -> None:
    """پس از هر تغییر محتوا در ادمین — داده برای کاربر بلافاصله تازه می‌شود."""
    cache.delete(INSTITUTE_CACHE_KEY)
    cache.delete(NAV_COUNTRIES_CACHE_KEY)
    cache.delete(HAS_ACTIVE_COURSES_CACHE_KEY)
    cache.delete(HAS_ACTIVE_COURSES_EXISTS_KEY)
    cache.delete(SERVICE_CATEGORIES_CACHE_KEY)
    cache.delete(PUBLIC_STATS_CACHE_KEY)
    cache.delete(PRICING_PAGE_CACHE_KEY)
    cache.delete(BLOG_TAGS_CACHE_KEY)
    try:
        cache.incr(BLOG_SEARCH_VERSION_KEY)
    except ValueError:
        cache.set(BLOG_SEARCH_VERSION_KEY, 2, None)
    try:
        cache.incr(SITE_NAV_VERSION_KEY)
    except ValueError:
        cache.set(SITE_NAV_VERSION_KEY, 2, None)
    invalidate_search_caches()
    invalidate_content_html_caches()
    from .browse_cache import invalidate_browse_counts

    invalidate_browse_counts()


def page_cache_seconds() -> int:
    return _seconds("PAGE_CACHE_SECONDS", 90)


def cached_page(view_func):
    """
    کش صفحه HTML با نسخه محتوا — ویرایش ادمین = نمایش فوری نسخه جدید.
  در حالت DEBUG پیش‌فرض خاموش است.
    """
    if not page_cache_enabled():

        @wraps(view_func)
        def _live(request, *args, **kwargs):
            return view_func(request, *args, **kwargs)

        return _live

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        ver = content_cache_version()
        cache_key = (view_func.__module__, view_func.__qualname__, ver)
        inner = _HTML_VIEW_CACHE.get(cache_key)
        if inner is None:
            inner = cache_page(
                page_cache_seconds(),
                key_prefix=f"html-c{ver}",
            )(view_func)
            _HTML_VIEW_CACHE[cache_key] = inner
        return inner(request, *args, **kwargs)

    return _wrapped
