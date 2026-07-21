"""
قوانین robots/noindex برای URLهای فیلتر و ردیابی — رفع هشدارهای GSC.
"""

from __future__ import annotations

from django.http import HttpRequest

# پارامترهایی که نسخهٔ فیلترشده نباید ایندکس شود
_FACET_QUERY_KEYS = frozenset(
    {
        "q",
        "tag",
        "page",
        "country",
        "university",
        "major",
        "about",
        "title",
        "category",
        "ref",
        "needs",
        "intent",
        "target_degree",
        "partial",
        "offset",
        "success",
    }
)

# مسیرهایی که با query string فقط noindex می‌شوند (خود صفحهٔ پایه index است)
_PARAM_SENSITIVE_PREFIXES = (
    "/ارزیابی-مهاجرت/",
    "/رزرو-مشاوره/",
    "/رشته-های-تحصیلی/",
    "/دانشگاه-های-خارج/",
    "/دوره-های-تحصیلی/",
    "/blog/",
    "/خدمات-با-ما/",
    "/سوالات-متداول/",
    "/تماس-با-ما/",
)

# همیشه noindex
_ALWAYS_NOINDEX_PREFIXES = (
    "/search/",
    "/ارزیابی-مهاجرت/نتیجه/",
    "/ارزیابی-مهاجرت/process/",
    "/ارزیابی-مهاجرت/submit/",
)


def request_has_facet_params(request: HttpRequest) -> bool:
    if not request.GET:
        return False
    return bool(set(request.GET.keys()) & _FACET_QUERY_KEYS)


def resolve_meta_robots(request: HttpRequest | None) -> str:
    """مقدار meta robots برای قالب base."""
    if request is None:
        return "index, follow"
    path = request.path or ""
    if any(path.startswith(prefix) for prefix in _ALWAYS_NOINDEX_PREFIXES):
        return "noindex, nofollow"
    if request_has_facet_params(request):
        if any(path.startswith(prefix) for prefix in _PARAM_SENSITIVE_PREFIXES):
            return "noindex, follow"
        if path.startswith("/blog/") and request.GET.get("tag"):
            return "noindex, follow"
    return "index, follow"


def private_robots_header() -> str:
    return "noindex, nofollow"
