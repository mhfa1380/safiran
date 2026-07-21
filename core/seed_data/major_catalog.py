"""
رشته‌های تحصیلی به تفکیک کشور — بر اساس لیست مرجع evaluation_majors.

هر کشور: لیست پایه + رشته‌های مشترک اعزام + رشته‌های اختصاصی همان مقصد،
با حذف تکرار عنوان و جایگزینی نسخه تخصصی‌تر (مثلاً MBBS در چین).
"""
from __future__ import annotations

from typing import Iterable

from core.evaluation_majors import EVALUATION_MAJOR_SUGGESTIONS
from core.study_destinations import (
    PRIMARY_STUDY_COUNTRY_CODES,
    WORLD_STUDY_COUNTRY_CODES,
    WORLD_STUDY_COUNTRY_LABELS,
)

ALL_MAJOR_COUNTRY_CODES: tuple[str, ...] = tuple(
    sorted(PRIMARY_STUDY_COUNTRY_CODES | set(WORLD_STUDY_COUNTRY_CODES))
)

# رشته‌های مشترک مقاصد اعزام (به همه کشورهای فعال اضافه می‌شوند)
GLOBAL_STUDY_ABROAD_MAJORS: tuple[str, ...] = (
    "اقتصاد بین‌الملل",
    "امنیت سایبری",
    "بازاریابی",
    "بهداشت عمومی",
    "بیوانفورماتیک",
    "حقوق تجارت بین‌الملل",
    "علوم اعصاب",
    "علوم داده",
    "علوم شناختی",
    "طراحی بازی و رسانه‌های تعاملی",
    "MBA و مدیریت کسب‌وکار",
    "مدیریت زنجیره تأمین",
    "مدیریت منابع انسانی",
    "مطالعات بین‌فرهنگی",
    "هنرهای دیجیتال",
    "هوانوردی",
    "هوش مصنوعی",
    "زبان‌شناسی کاربردی",
    "روان‌شناسی شناختی",
)

# رشته‌های اختصاصی هر کشور (پس از اعمال EXCLUDE)
_COUNTRY_EXTRA: dict[str, tuple[str, ...]] = {
    "canada": (
        "مدیریت بین‌الملل",
        "مهندسی منابع طبیعی و جنگل",
        "علوم محیطی",
    ),
    "spain": (
        "گردشگری",
        "هتلداری",
        "علوم ورزشی کاربردی",
        "زبان و ادبیات اسپانیایی",
        "مدیریت هتل و مهمان‌نوازی",
    ),
    "china": (
        "پزشکی عمومی (MBBS)",
        "دندانپزشکی عمومی",
        "داروسازی بالینی",
        "زبان چینی",
        "طب سنتی چین",
        "مهندسی نساجی و پوشاک",
        "علوم و مهندسی غذایی",
    ),
}

# رشته‌های تکمیلی برای کشورهای پرطرفدار (سایر کشورها)
_WORLD_COUNTRY_EXTRA: dict[str, tuple[str, ...]] = {
    "uk": ("حقوق انگلیس", "مدیریت بین‌الملل"),
    "usa": ("MBA و مدیریت کسب‌وکار",),
    "germany": ("مهندسی مکانیک", "علوم داده"),
    "australia": ("مهندسی عمران", "پرستاری"),
    "france": ("مدیریت هتل و مهمان‌نوازی",),
    "netherlands": ("علوم داده", "MBA و مدیریت کسب‌وکار"),
    "japan": ("مهندسی برق", "علوم داده"),
    "south_korea": ("مهندسی کامپیوتر", "MBA و مدیریت کسب‌وکار"),
    "italy": ("معماری", "طراحی صنعتی"),
    "malaysia": ("MBA و مدیریت کسب‌وکار",),
    "turkey": ("MBA و مدیریت کسب‌وکار",),
    "uae": ("MBA و مدیریت کسب‌وکار", "مدیریت بین‌الملل"),
}

# از لیست پایه حذف می‌شوند تا نسخه تخصصی‌تر همان کشور جایگزین شود
_COUNTRY_EXCLUDE: dict[str, frozenset[str]] = {
    "china": frozenset(
        {
            "پزشکی",
            "دندانپزشکی",
            "داروسازی",
        }
    ),
}


def _normalize_title(title: str) -> str:
    return (title or "").strip()


def _dedupe_preserve_order(titles: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for raw in titles:
        t = _normalize_title(raw)
        if not t or t in seen:
            continue
        seen.add(t)
        result.append(t)
    return result


def get_majors_for_country(country_code: str) -> list[str]:
    """تمام رشته‌های یک کشور — بدون تکرار عنوان، مرتب‌شده الفبایی."""
    exclude = _COUNTRY_EXCLUDE.get(country_code, frozenset())
    base = [t for t in EVALUATION_MAJOR_SUGGESTIONS if _normalize_title(t) not in exclude]
    extras = (
        *GLOBAL_STUDY_ABROAD_MAJORS,
        *_COUNTRY_EXTRA.get(country_code, ()),
        *_WORLD_COUNTRY_EXTRA.get(country_code, ()),
    )
    merged = _dedupe_preserve_order((*base, *extras))
    return sorted(merged, key=lambda s: s.strip())


def get_all_catalog_slugs() -> dict[str, set[str]]:
    """slugهای مورد انتظار به تفکیک کشور — برای prune در seed."""
    from core.seed_data.content_builders import major_slug

    out: dict[str, set[str]] = {}
    for code in ALL_MAJOR_COUNTRY_CODES:
        out[code] = {major_slug(code, t) for t in get_majors_for_country(code)}
    return out


MAJORS_BY_COUNTRY: dict[str, list[str]] = {
    code: get_majors_for_country(code) for code in ALL_MAJOR_COUNTRY_CODES
}


def get_country_label(country_code: str) -> str:
    from core.seed_data.university_catalog import COUNTRY_LABELS

    if country_code in COUNTRY_LABELS:
        return COUNTRY_LABELS[country_code]
    return WORLD_STUDY_COUNTRY_LABELS.get(country_code, country_code)
