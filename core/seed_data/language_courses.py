"""
کاتالوگ دوره‌های زبان (مسیر TOEFL) — برای seed و پیشنهاد در ارزیابی هوشمند.
"""
from __future__ import annotations

from typing import Any

from core.models import Course

TOEFL_PATHWAY_SLUGS: tuple[str, ...] = (
    "toefl-learning-method",
    "toefl-pre-foundation-a",
    "toefl-core-package-b",
    "toefl-score-booster-c",
)

TOEFL_PATHWAY_META: dict[str, dict[str, Any]] = {
    "toefl-learning-method": {
        "category": "متد یادگیری",
        "level_label": "همه سطوح (A1 تا C2)",
        "target_toefl": None,
        "target_toefl_label": "",
        "sessions": 3,
        "weeks": 3,
        "skills": ("W", "S", "L", "R"),
        "badge": "LEARNING METHOD",
    },
    "toefl-pre-foundation-a": {
        "category": "پایه و آمادگی",
        "level_label": "A2 تا B1",
        "target_toefl": 55,
        "target_toefl_label": "هدف تافل ۵۵+",
        "sessions": 36,
        "weeks": 12,
        "skills": ("W", "S", "L", "R"),
        "badge": "FOUNDATION",
    },
    "toefl-core-package-b": {
        "category": "آمادگی تافل",
        "level_label": "B1+ تا B2",
        "target_toefl": 70,
        "target_toefl_label": "هدف تافل ۷۰+",
        "sessions": 30,
        "weeks": 10,
        "skills": ("W", "S", "L", "R"),
        "badge": "TOEFL PREP",
    },
    "toefl-score-booster-c": {
        "category": "آمادگی تافل",
        "level_label": "B2",
        "target_toefl": 78,
        "target_toefl_label": "هدف تافل ۷۸+",
        "sessions": 12,
        "weeks": 4,
        "skills": ("W", "S", "L", "R"),
        "badge": "TOEFL PREP",
    },
}

LANGUAGE_COURSE_SEED: list[dict[str, Any]] = [
    {
        "slug": "toefl-learning-method",
        "title": "چگونه زبان یاد بگیریم؟ (۳ جلسه‌ای)",
        "short_description": (
            "پیشنهاد ویژه برای همه سطوح — قبل از شروع تافل یا هر مسیر مهاجرت، "
            "روش یادگیری مؤثر زبان را در ۳ جلسه یاد بگیرید."
        ),
        "description": (
            "در این دوره کوتاه با اصول یادگیری زبان، برنامه‌ریزی روزانه و "
            "تکنیک‌های تقویت چهار مهارت آشنا می‌شوید — مناسب همه سطوح از A1 تا C2."
        ),
        "objectives": "آشنایی با متد یادگیری زبان؛ برنامه‌ریزی شخصی؛ آمادگی ذهنی برای دوره‌های تافل",
        "conditions": "بدون پیش‌نیاز — همه سطوح",
        "features": "\n".join(
            [
                "دسته: متد یادگیری",
                "۳ جلسه طی ۳ هفته",
                "مناسب همه سطوح A1 تا C2",
                "پیشنهاد قبل از شروع مسیر تافل",
            ]
        ),
        "price": "۳۵۰,۰۰۰ تومان",
        "duration_hours": 3,
        "order": 1,
        "is_active": True,
        "delivery_mode": Course.DELIVERY_ONLINE,
        "country": "",
    },
    {
        "slug": "toefl-pre-foundation-a",
        "title": "آمادگی برای تافل – دوره پری‌تافل A1/A2 (+ → B1) – پکیج A",
        "short_description": (
            "پکیج A | مسیر پایه تا آمادگی تافل | ۳۶ جلسه — "
            "از سطح مقدماتی تا B1 و هدف نمره تافل حدود ۵۵."
        ),
        "description": (
            "دوره پایه و آمادگی برای ورود به مسیر تافل؛ تقویت گرامر، واژگان و "
            "مهارت‌های چهارگانه از سطح A2 به سمت B1 با تمرکز بر آزمون TOEFL iBT."
        ),
        "objectives": "رسیدن به سطح B1؛ آمادگی اولیه برای TOEFL iBT؛ هدف نمره تافل ۵۵+",
        "conditions": "سطح A2 یا مبتدی با انگیزه بالا",
        "features": "\n".join(
            [
                "دسته: پایه و آمادگی",
                "۳۶ جلسه طی ۱۲ هفته",
                "سطح A2 تا B1",
                "هدف تافل ۵۵+",
            ]
        ),
        "price": "۷,۵۰۰,۰۰۰ تومان",
        "duration_hours": 36,
        "order": 2,
        "is_active": True,
        "delivery_mode": Course.DELIVERY_BOTH,
        "country": "",
    },
    {
        "slug": "toefl-core-package-b",
        "title": "هسته آماده‌سازی تافل (TOEFL Core) – پکیج B",
        "short_description": (
            "از B1+ تا نمره ۷۰–۸۰ در تافل | ۳۰ جلسه — "
            "بخش اصلی مسیر آمادگی تافل با تمرکز بر چهار مهارت iBT."
        ),
        "description": (
            "دوره هسته آمادگی تافل برای داوطلبانی که پایه زبان دارند و "
            "می‌خواهند به نمره ۷۰ تا ۸۰ در TOEFL iBT برسند."
        ),
        "objectives": "تقویت Reading، Listening، Speaking، Writing؛ هدف نمره تافل ۷۰+",
        "conditions": "حداقل سطح B1+ یا گذراندن پکیج A",
        "features": "\n".join(
            [
                "دسته: آمادگی تافل",
                "۳۰ جلسه طی ۱۰ هفته",
                "سطح B1+ تا B2",
                "هدف تافل ۷۰+",
            ]
        ),
        "price": "۸,۹۰۰,۰۰۰ تومان",
        "duration_hours": 30,
        "order": 3,
        "is_active": True,
        "delivery_mode": Course.DELIVERY_BOTH,
        "country": "",
    },
    {
        "slug": "toefl-score-booster-c",
        "title": "تافل Score Booster – Mock Camp (پکیج C)",
        "short_description": (
            "افزایش نمره نهایی تافل | ۱۲ جلسه فشرده — "
            "Mock Camp برای رسیدن به هدف ۷۸+ با تمرین آزمون‌های شبیه‌سازی‌شده."
        ),
        "description": (
            "پکیج C برای داوطلبان سطح B2 که نمره فعلی نزدیک هدف است و "
            "به تمرین فشرده Mock و بازخورد تخصصی نیاز دارند."
        ),
        "objectives": "افزایش نمره نهایی تافل؛ آشنایی با فشار زمانی آزمون؛ هدف ۷۸+",
        "conditions": "سطح B2 یا نمره تافل بالای ۶۵",
        "features": "\n".join(
            [
                "دسته: آمادگی تافل",
                "۱۲ جلسه طی ۴ هفته",
                "سطح B2",
                "هدف تافل ۷۸+",
            ]
        ),
        "price": "۴,۵۰۰,۰۰۰ تومان",
        "duration_hours": 12,
        "order": 4,
        "is_active": True,
        "delivery_mode": Course.DELIVERY_BOTH,
        "country": "",
    },
]


def seed_language_courses(*, stdout_write=None) -> dict[str, int]:
    """ایجاد یا به‌روزرسانی دوره‌های مسیر TOEFL."""
    created = updated = 0
    for row in LANGUAGE_COURSE_SEED:
        slug = row["slug"]
        defaults = {k: v for k, v in row.items() if k != "slug"}
        course, was_created = Course.objects.update_or_create(slug=slug, defaults=defaults)
        if was_created:
            created += 1
        else:
            updated += 1
        if stdout_write:
            stdout_write(f"  {'+' if was_created else '~'} {slug}")
    return {"created": created, "updated": updated}
