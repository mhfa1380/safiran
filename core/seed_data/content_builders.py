"""Generate SEO-rich Persian HTML content for universities and majors."""
from __future__ import annotations

import hashlib
import re

from django.utils.text import slugify

from .rich_content import (
    build_rich_major_description as build_major_description,
    build_rich_major_faqs as build_major_faqs,
    build_rich_major_short as build_major_short,
    build_rich_university_description as build_university_description,
    build_rich_university_faqs as build_university_faqs,
    build_rich_university_short as build_university_short,
)

from .seo_content_shared import COUNTRY_SEO_HOOKS as _COUNTRY_SEO_HOOKS, evaluation_href as _evaluation_href


def major_slug(country_code: str, title: str) -> str:
    """Stable unique slug for Persian/English major titles."""
    base = slugify(title, allow_unicode=True)
    if not base:
        base = slugify(title, allow_unicode=False)
    if not base:
        digest = hashlib.md5(title.encode("utf-8")).hexdigest()[:10]
        base = f"r{digest}"
    base = re.sub(r"-+", "-", base).strip("-")
    return f"{country_code}-{base}"[:250]


def build_university_meta_title(uni: dict, country_label: str, country_code: str = "") -> str:
    hook, _ = _COUNTRY_SEO_HOOKS.get(country_code, ("پذیرش ۲۰۲۶", ""))
    rank = (uni.get("world_rank") or "").strip()
    name = uni["name_fa"]
    if rank and str(rank).isdigit():
        return f"{name} | رتبه {rank} QS — {hook} ({country_label})"
    return f"{name} | {hook} — اپلای ایرانی ({country_label})"


def build_university_meta_description(uni: dict, country_label: str, country_code: str = "") -> str:
    _, extra = _COUNTRY_SEO_HOOKS.get(country_code, ("", "ویزای تحصیلی"))
    rank = (uni.get("world_rank") or "").strip()
    rank_text = f"رتبه QS {rank}، " if rank else ""
    city = (uni.get("city") or "").strip()
    city_text = f"{city} — " if city else ""
    text = (
        f"اپلای {uni['name_fa']}: {city_text}{rank_text}"
        f"شهریه، {extra}، پذیرش ایرانی ۲۰۲۶. مشاوره رایگان — سفیران."
    )
    return text[:160]


def build_major_meta_title(title: str, country_label: str, country_code: str = "") -> str:
    hook, _ = _COUNTRY_SEO_HOOKS.get(country_code, ("پذیرش ۲۰۲۶", ""))
    return f"تحصیل {title} در {country_label} | {hook}"


def build_major_meta_description(title: str, country_label: str, country_code: str = "") -> str:
    from .rich_content import build_major_summary_answer

    text = build_major_summary_answer(title, country_code, country_label)
    if len(text) > 157:
        return text[:157].rstrip() + "…"
    return text
