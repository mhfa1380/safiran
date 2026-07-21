"""سئو صفحات نتیجه ارزیابی — لینک خصوصی؛ noindex و canonical به صفحه عمومی."""

from __future__ import annotations

from typing import Any

from django.urls import reverse

# لینک اشتراک نتیجه نباید در گوگل ایندکس شود
PRIVATE_ROBOTS = "noindex, nofollow, noarchive"
PRIVATE_ROBOTS_HEADER = "noindex, nofollow, noarchive"


def _evaluation_landing_url(site_url: str) -> str:
    base = site_url.rstrip("/")
    return f"{base}{reverse('evaluation')}"


def build_evaluation_result_page_seo(
    *,
    institute_name: str,
    site_url: str,
) -> dict[str, Any]:
    landing_url = _evaluation_landing_url(site_url)
    meta_description = (
        f"گزارش شخصی ارزیابی مهاجرت تحصیلی — لینک خصوصی {institute_name}. "
        "برای ارزیابی رایگان جدید به فرم ارزیابی آنلاین مراجعه کنید."
    )
    return {
        "eval_result_meta_robots": PRIVATE_ROBOTS,
        "eval_result_meta_description": meta_description,
        "eval_result_canonical_url": landing_url,
        "eval_landing_url": landing_url,
    }


def build_evaluation_expired_page_seo(
    *,
    institute_name: str,
    site_url: str,
) -> dict[str, Any]:
    landing_url = _evaluation_landing_url(site_url)
    meta_description = (
        f"اعتبار لینک نتیجه ارزیابی به پایان رسیده است. "
        f"فرم ارزیابی رایگان مهاجرت تحصیلی {institute_name} را دوباره تکمیل کنید."
    )
    return {
        "eval_result_meta_robots": PRIVATE_ROBOTS,
        "eval_result_meta_description": meta_description,
        "eval_result_canonical_url": landing_url,
        "eval_landing_url": landing_url,
    }
