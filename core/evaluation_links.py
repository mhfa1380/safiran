"""لینک‌های ارزیابی هوشمند با پارامترهای پیش‌فرض (کشور، رشته، دانشگاه)."""
from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

from django.urls import reverse

from .nav_degrees import append_query_params


def build_evaluation_url(
    *,
    country: str = "",
    major: str = "",
    university: str = "",
    ref: str = "",
    target_degree: str = "",
    intent: str = "",
) -> str:
    """URL صفحه ارزیابی با query string برای پیش‌پر کردن فرم."""
    params: dict[str, str] = {}
    if country:
        params["country"] = country.strip()
    if major:
        params["major"] = major.strip()
    if university:
        params["university"] = university.strip()
    if ref:
        params["ref"] = ref.strip()
    if target_degree:
        params["target_degree"] = target_degree.strip()
    if intent:
        params["intent"] = intent.strip()
    base = reverse("evaluation")
    if not params:
        return base
    return append_query_params(base, params)


def parse_evaluation_prefill_params(get) -> dict[str, Any]:
    """خواندن پارامترهای ورود از query string (صفحات دانشگاه/رشته)."""
    country = (get.get("country") or "").strip().lower()
    major = (get.get("major") or get.get("field_of_study") or "").strip()
    university = (get.get("university") or "").strip()
    ref = (get.get("ref") or "").strip()
    valid_countries = {"canada", "spain", "china", "germany", "italy", "not_sure", "other"}
    return {
        "eval_prefill_country": country if country in valid_countries else "",
        "eval_prefill_major": major[:200],
        "eval_prefill_university": university[:150],
        "eval_ref_source": ref[:100],
    }
