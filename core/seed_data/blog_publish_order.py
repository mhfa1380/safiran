"""
ترتیب محبوبیت پست‌های وبلاگ موجود (برای زمان‌بندی انتشار).
هرچه بالاتر در لیست = جدیدتر (امروز و دیروز).
"""

from __future__ import annotations

# ۳۳ پست فعلی — از پرجستجو/تبدیل به کم‌اولویت
BLOG_POPULARITY_ORDER: list[str] = [
    # امروز و دیروز — پرطرفدارترین
    "free-online-study-abroad-evaluation-smart-report",
    "canada-immigration-study-permit-updates-2025-2026",
    "china-csc-scholarship-application-guide-2026",
    "canada-gic-financial-requirements-study-visa-2025",
    "canada-pgwp-post-graduation-work-permit-guide-2025",
    "study-abroad-without-language-certificate",
    "iranian-degree-validity-abroad-apply",
    "compare-canada-spain-china-study-abroad-2025",
    "spain-student-visa-type-d-checklist-2025",
    "china-student-visa-x1-x2-requirements-2025",
    "best-time-start-study-abroad-canada",
    "canada-best-provinces-cities-international-students-2025",
    "canada-part-time-jobs-international-students-rules-2025",
    "online-study-abroad-consultation-guide",
    "free-consultation-vs-evaluation-study-abroad",
    "12-month-checklist-before-study-abroad-departure",
    "study-abroad-immigration-news-iranians-2025-1404",
    "spain-cost-living-madrid-barcelona-students-2025",
    "china-cost-living-beijing-shanghai-guangzhou-2025",
    "spain-scholarships-grants-international-students-2025",
    "china-hsk-levels-university-requirements",
    "spain-learn-spanish-study-abroad-dele-siele",
    "spain-nie-empadronamiento-students-step-by-step",
    "canada-winter-survival-guide-iranian-students",
    "halal-food-muslim-students-canada-spain-china",
    "student-life-culture-canada-spain-china",
    "local-food-guide-canada-spain-china-students",
    "canada-iconic-foods-poutine-maple-student-guide",
    "spain-tapas-paella-regional-food-student-guide",
    "china-regional-cuisine-student-food-guide",
    "china-spring-festival-international-student-experience",
    "spain-festivals-culture-student-calendar-2025",
]

# ۳۲ مقاله محتوایی (بدون لندینگ ارزیابی) — برای تصویر اختصاصی
BLOG_ORIGINAL_32_SLUGS: frozenset[str] = frozenset(
    s for s in BLOG_POPULARITY_ORDER if s != "free-online-study-abroad-evaluation-smart-report"
)

# پیلارهای plan_200 با اولویت بالا (بعد از ۳۳ پست قبلی، قبل از بقیه plan)
PLAN_HIGH_PRIORITY_SLUGS: list[str] = [
    "study-in-canada-2026-complete-guide",
    "study-germany-free-tuition-2026",
    "china-csc-scholarship-application-guide-2026",
    "germany-student-visa-2026",
    "canada-study-permit-2026",
    "canada-visa-refusal-fix-2026",
    "study-usa-f1-visa-2026",
    "cost-study-living-canada-2026",
    "what-is-sop-how-to-write",
    "study-visa-refusal-reasons-solutions",
    "canada-vs-usa-study-abroad-2026",
    "germany-vs-netherlands-study-2026",
    "financial-proof-study-visa-guide",
    "best-european-country-study-abroad-2026",
    "total-cost-study-abroad-2026",
]


def build_full_popularity_order() -> list[str]:
    """
    ترتیب کامل محبوبیت: قدیمی‌های پرترافیک → پیلارهای plan → بقیه plan بر اساس id.
    """
    from pathlib import Path

    import json

    from django.conf import settings

    order: list[str] = []
    seen: set[str] = set()

    def add(slug: str) -> None:
        if slug and slug not in seen:
            order.append(slug)
            seen.add(slug)

    for slug in BLOG_POPULARITY_ORDER:
        add(slug)
    for slug in PLAN_HIGH_PRIORITY_SLUGS:
        add(slug)

    plan_path = Path(settings.BASE_DIR) / "data" / "blog_seo_plan" / "plan_200.json"
    if plan_path.is_file():
        try:
            data = json.loads(plan_path.read_text(encoding="utf-8"))
            articles = sorted(
                data.get("articles", []),
                key=lambda x: int(x.get("id", 9999)),
            )
            for item in articles:
                add(item.get("slug", ""))
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            pass

    return order
