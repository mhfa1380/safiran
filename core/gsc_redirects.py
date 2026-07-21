"""
ریدایرکت ۳۰۱ آدرس‌های قدیمی GSC — اسلاگ‌های legacy و تکراری.
"""

from __future__ import annotations

import re

from django.http import HttpResponsePermanentRedirect
from django.urls import reverse

# اسلاگ‌های قدیمی دانشگاه (seed_fixture_data / نسخه اول سایت)
LEGACY_UNIVERSITY_SLUG_REDIRECTS: dict[str, str] = {
    "ubc": "university-of-british-columbia",
    "ub-barcelona": "universitat-de-barcelona",
}

# اسلاگ‌های قدیمی رشته — به لیست رشته‌ها
LEGACY_MAJOR_SLUG_REDIRECTS: frozenset[str] = frozenset(
    {"medicine", "dentistry", "computer-science"}
)

# اسلاگ‌های تکراری seed (boston-university-2، …-3) → نسخهٔ اصلی بدون پسوند عددی
_DUPLICATE_SLUG_SUFFIX = re.compile(r"^(?P<base>.+)-(?P<num>[2-9]\d*)$")


def _redirect_to(name: str, **kwargs) -> HttpResponsePermanentRedirect:
    return HttpResponsePermanentRedirect(reverse(name, kwargs=kwargs))


def try_gsc_legacy_redirect(request):
    """
    اگر مسیر legacy باشد HttpResponsePermanentRedirect برمی‌گرداند؛ وگرنه None.
    """
    path = (request.path or "").rstrip("/")
    if not path:
        return None

    parts = [p for p in path.split("/") if p]
    if len(parts) != 2:
        return None

    section, slug = parts[0], parts[1]
    if section == "دانشگاه":
        target = LEGACY_UNIVERSITY_SLUG_REDIRECTS.get(slug)
        if target:
            return _redirect_to("school_detail", slug=target)
        m = _DUPLICATE_SLUG_SUFFIX.match(slug)
        if m:
            return _redirect_to("school_detail", slug=m.group("base"))
    elif section == "رشته" and slug in LEGACY_MAJOR_SLUG_REDIRECTS:
        return HttpResponsePermanentRedirect(reverse("majors"))

    return None
