"""
پیشنهاد هوشمند دوره‌های زبان (مسیر TOEFL) برای گزارش ارزیابی.
"""
from __future__ import annotations

from typing import Any

from django.urls import reverse

from .models import Course, EvaluationRequest
from .seed_data.language_courses import TOEFL_PATHWAY_META, TOEFL_PATHWAY_SLUGS

_SKILL_LABELS = {
    "R": "Reading",
    "L": "Listening",
    "S": "Speaking",
    "W": "Writing",
}

_TIER_SLUGS: dict[str, list[str]] = {
    "start": ["toefl-learning-method", "toefl-pre-foundation-a"],
    "pre": ["toefl-pre-foundation-a", "toefl-learning-method"],
    "core": ["toefl-core-package-b", "toefl-pre-foundation-a"],
    "booster": ["toefl-score-booster-c", "toefl-core-package-b"],
    "strong": ["toefl-score-booster-c"],
}

_TIER_REASONS: dict[str, list[str]] = {
    "start": [
        "بدون مدرک زبان یا سطح پایین — شروع از متد یادگیری و پایه تافل منطقی‌ترین قدم است.",
        "قبل از اپلای، تقویت زبان انگلیسی اولویت عملی پرونده شماست.",
    ],
    "pre": [
        "با سطح فعلی، دوره پری‌تافل پل مناسبی تا رسیدن به B1 و نمره تافل ۵۵+ است.",
        "تقویت پایه زبان قبل از دوره‌های فشرده تافل، شانس پذیرش را بالا می‌برد.",
    ],
    "core": [
        "پایه زبان شما برای ورود به دوره هسته تافل (پکیج B) مناسب است.",
        "هدف بعدی: نمره تافل ۷۰+ برای بسیاری از دانشگاه‌های مقصد.",
    ],
    "booster": [
        "نمره زبان نزدیک به حد نصاب است — Mock Camp برای جهش نهایی به ۷۸+ پیشنهاد می‌شود.",
        "تمرین آزمون‌های شبیه‌سازی‌شده، ضعف‌های باقی‌مانده را سریع‌تر پوشش می‌دهد.",
    ],
    "strong": [
        "نمره زبان پرونده شما نسبتاً خوب است؛ در صورت نیاز به تافل رسمی، پکیج C برای تثبیت نمره مفید است.",
        "حتی با زبان قوی، تمرین Mock قبل از آزمون رسمی توصیه می‌شود.",
    ],
}

_INTRO_LEAD = (
    "گزارش شما آماده است؛ اما در پرونده‌های واقعی، "
    "<strong>ضعیف‌ترین حلقه اغلب زبان است</strong> — نه کشور و نه رشته. "
    "هر ماه تأخیر در زبان، یعنی یک موج اپلای کمتر و شانس بورسیه پایین‌تر."
)

_INTRO_TITLE_SUBTLE = "دوره‌های تکمیلی زبان"
_INTRO_LEAD_SUBTLE = (
    "مدرک زبان در پرونده ثبت شده است. در صورت نیاز به تقویت یا آمادگی آزمون، "
    "این دوره‌ها می‌توانند مکمل مسیر شما باشند:"
)

_TIER_URGENCY: dict[str, dict[str, Any]] = {
    "start": {
        "eyebrow": "نقطه حساس پرونده",
        "headline": "الان شروع نکنید، احتمالاً سال دیگر هنوز سرِ همین نقطه‌اید.",
        "chips": (
            "بدون مدرک زبان، پرونده در مرحله اول متوقف می‌شود",
            "اپلای بدون زبان = ریسک رد شدن یا تعویق پذیرش",
            "شروع زودتر = زمان بیشتر برای تافل و بورسیه",
        ),
        "social": "بیشتر متقاضیانی که از صفر شروع کردند، اول سراغ «متد یادگیری» رفتند.",
    },
    "pre": {
        "eyebrow": "پل تا نمره قابل قبول",
        "headline": "با این سطح، پذیرش بدون تقویت زبان ریسک بالایی دارد.",
        "chips": (
            "سطح فعلی برای بسیاری از دانشگاه‌ها کافی نیست",
            "پری‌تافل، فاصله تا B1 و تافل ۵۵+ را کوتاه می‌کند",
            "هر ترم تأخیر، رقبا را جلو می‌اندازد",
        ),
        "social": "متقاضیان با سطح مشابه شما، معمولاً از پکیج پری‌تافل شروع کردند.",
    },
    "core": {
        "eyebrow": "نزدیک به حد نصاب",
        "headline": "پایه دارید؛ حالا چند ماه فشرده می‌تواند درِ دانشگاه را باز کند.",
        "chips": (
            "هدف بعدی: تافل ۷۰+ برای دانشگاه‌های جدی",
            "با برنامه درست، جهش نمره قابل پیش‌بینی است",
            "تأخیر در این مرحله = از دست دادن intake بعدی",
        ),
        "social": "در این سطح، دوره هسته تافل پرتکرارترین قدم متقاضیان موفق است.",
    },
    "booster": {
        "eyebrow": "فاصله تا نمره هدف",
        "headline": "فقط چند نمره فاصله دارید — Mock Camp می‌تواند همان تفاوت را بسازد.",
        "chips": (
            "نمره نزدیک به حد نصاب، بدون تمرین آزمون ریسک دارد",
            "شبیه‌سازی آزمون، ضعف‌های پنهان را لو می‌دهد",
            "یک بار آزمون اضافه = هزینه و زمان بیشتر",
        ),
        "social": "متقاضیان با نمره نزدیک، Mock Camp را قبل از آزمون رسمی می‌گذرانند.",
    },
    "strong": {
        "eyebrow": "تثبیت نمره",
        "headline": "زبان خوب دارید؛ تمرین هدفمند قبل از آزمون رسمی هنوز ارزش دارد.",
        "chips": (
            "نمره خوب بدون تمرین آزمون، تضمین نیست",
            "تثبیت نمره = آرامش در مرحله ویزا و پذیرش",
            "یک دوره کوتاه، هزینه دوباره‌کاری را کم می‌کند",
        ),
        "social": "حتی با زبان قوی، Mock قبل از آزمون رسمی توصیه می‌شود.",
    },
}


def _pathway_tier(profile) -> str:
    """تعیین سطح مسیر بر اساس مدرک زبان و نمره."""
    ev = profile.eval_req
    equiv = profile.lang_ielts_equiv
    raw = profile.lang_score

    if ev.language_test_type == EvaluationRequest.TEST_TOEFL and raw is not None:
        if raw < 55:
            return "pre" if raw >= 40 else "start"
        if raw < 70:
            return "core"
        if raw < 78:
            return "booster"
        return "strong"

    if not profile.has_language_cert or equiv is None:
        return "start"
    if equiv < 4.5:
        return "start"
    if equiv < 5.5:
        return "pre"
    if equiv < 6.0:
        return "core"
    if equiv < 6.5:
        return "booster"
    return "strong"


def _load_pathway_courses() -> dict[str, Course]:
    rows = Course.objects.filter(slug__in=TOEFL_PATHWAY_SLUGS, is_active=True)
    return {c.slug: c for c in rows}


def _serialize_course(
    course: Course | None,
    slug: str,
    *,
    is_primary: bool,
    reasons: list[str],
) -> dict[str, Any]:
    meta = TOEFL_PATHWAY_META.get(slug, {})
    title = course.title if course else slug
    short = (course.short_description or "") if course else ""
    price = (course.price or "") if course else ""
    image = (course.image or "") if course else ""
    url = course.get_course_url() if course else reverse("courses_list")

    skills = meta.get("skills") or ("W", "S", "L", "R")
    return {
        "id": course.pk if course else None,
        "slug": slug,
        "title": title,
        "short_description": short[:220],
        "image": image,
        "price": price,
        "url": url,
        "category": meta.get("category") or "",
        "level_label": meta.get("level_label") or "",
        "target_toefl": meta.get("target_toefl"),
        "target_toefl_label": meta.get("target_toefl_label") or "",
        "sessions": meta.get("sessions") or 0,
        "weeks": meta.get("weeks") or 0,
        "skills": list(skills),
        "skill_labels": [_SKILL_LABELS.get(s, s) for s in skills],
        "badge": meta.get("badge") or "",
        "is_primary": is_primary,
        "is_featured": is_primary,
        "reasons": reasons[:2],
    }


def build_language_pathway(
    profile,
    *,
    country_code: str = "",
    limit: int = 3,
) -> dict[str, Any]:
    """مسیر پیشنهادی دوره زبان — همیشه نمایش داده می‌شود."""
    from .evaluation_engine import ApplicantProfile

    courses_list_url = reverse("courses_list")
    base: dict[str, Any] = {
        "show": True,
        "intro_title": "آخرش چی می‌شه؟",
        "intro_lead": _INTRO_LEAD,
        "urgency_eyebrow": "",
        "urgency_headline": "",
        "urgency_chips": (),
        "social_proof": "",
        "pathway_note": "",
        "tier": "",
        "has_language_cert": False,
        "prominence": "high",
        "courses": [],
        "courses_list_url": courses_list_url,
    }

    if not isinstance(profile, ApplicantProfile):
        return {**base, "show": False}

    tier = _pathway_tier(profile)
    has_cert = bool(profile.has_language_cert)
    prominence = "low" if has_cert else "high"
    course_limit = 2 if has_cert else limit

    slug_order = _TIER_SLUGS.get(tier, list(TOEFL_PATHWAY_SLUGS))
    tier_reasons = _TIER_REASONS.get(tier, _TIER_REASONS["start"])
    urgency = _TIER_URGENCY.get(tier, _TIER_URGENCY["start"])
    base["tier"] = tier
    base["has_language_cert"] = has_cert
    base["prominence"] = prominence
    base["pathway_note"] = tier_reasons[0]

    if prominence == "low":
        base["intro_title"] = _INTRO_TITLE_SUBTLE
        base["intro_lead"] = _INTRO_LEAD_SUBTLE
        base["social_proof"] = urgency.get("social", "") if tier != "strong" else ""
    else:
        base["urgency_eyebrow"] = urgency.get("eyebrow", "")
        base["urgency_headline"] = urgency.get("headline", "")
        base["urgency_chips"] = urgency.get("chips", ())
        base["social_proof"] = urgency.get("social", "")

    by_slug = _load_pathway_courses()
    if not by_slug:
        fallback = list(
            Course.objects.filter(is_active=True)
            .filter(title__icontains="تافل")
            .order_by("order", "id")[:course_limit]
        )
        if not fallback:
            fallback = list(Course.objects.filter(is_active=True).order_by("order", "id")[:course_limit])
        base["courses"] = [
            _serialize_course(c, c.slug, is_primary=i == 0, reasons=[tier_reasons[0]])
            for i, c in enumerate(fallback[:course_limit])
        ]
        return base

    seen: set[str] = set()
    ordered_slugs: list[str] = []
    for slug in slug_order:
        if slug not in seen:
            seen.add(slug)
            ordered_slugs.append(slug)
    for slug in TOEFL_PATHWAY_SLUGS:
        if slug not in seen and slug in by_slug:
            ordered_slugs.append(slug)

    courses_out: list[dict[str, Any]] = []
    for i, slug in enumerate(ordered_slugs[:course_limit]):
        course = by_slug.get(slug)
        if not course and slug not in TOEFL_PATHWAY_META:
            continue
        reason = tier_reasons[0] if i == 0 else (tier_reasons[1] if len(tier_reasons) > 1 else tier_reasons[0])
        courses_out.append(
            _serialize_course(
                course,
                slug,
                is_primary=i == 0,
                reasons=[reason],
            )
        )

    base["courses"] = courses_out
    return base


def pick_language_courses(
    profile,
    *,
    country_code: str = "",
    limit: int = 3,
) -> list[dict[str, Any]]:
    """سازگاری با گزارش ارزیابی — لیست دوره‌های پیشنهادی."""
    return build_language_pathway(profile, country_code=country_code, limit=limit).get(
        "courses", []
    )
