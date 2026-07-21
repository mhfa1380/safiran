"""Query helpers for university ↔ major bidirectional links."""
from __future__ import annotations

from django.db.models import Prefetch
from django.urls import reverse

from .models import Major, University, UniversityMajorLink
PREVIEW_MAJORS_PER_CATEGORY = 3

MAJOR_CATEGORY_LABELS: dict[str, str] = {
    "medical": "پزشکی و سلامت",
    "engineering": "مهندسی و فناوری",
    "business": "مدیریت و بازرگانی",
    "arts": "هنر و طراحی",
    "architecture": "معماری و شهرسازی",
    "science": "علوم پایه",
    "education": "آموزش و تربیتی",
    "agriculture": "کشاورزی و منابع",
    "law": "حقوق",
    "language": "زبان و ادبیات",
    "general": "سایر رشته‌ها",
}

MAJOR_CATEGORY_ORDER: tuple[str, ...] = (
    "engineering",
    "medical",
    "business",
    "science",
    "architecture",
    "arts",
    "law",
    "education",
    "agriculture",
    "language",
    "general",
)


def classify_major_display_group(title: str) -> str:
    """دسته‌بندی نمایشی رشته — مستقل از منطق seed تصویر."""
    t = (title or "").strip()
    if any(k in t for k in ("پزشکی", "دندان", "پرستاری", "دارو", "بهداشت", "دامپزشکی", "فیزیوتراپی", "MBBS")):
        return "medical"
    if any(k in t for k in ("MBA", "مدیریت", "اقتصاد", "حسابداری", "بازاریابی", "بازرگانی", "مالی", "کارآفرینی")):
        return "business"
    if "حقوق" in t:
        return "law"
    if any(k in t for k in ("زبان", "ادبیات", "ترجمه", "ژاپنی", "چینی", "اسپانیایی", "انگلیسی", "فرانسه", "آلمانی")):
        return "language"
    if any(k in t for k in ("آموزش", "تربیتی")) and "مشاوره" not in t:
        return "education"
    if any(k in t for k in ("کشاورزی", "منابع طبیعی", "باغبانی", "شیلات")):
        return "agriculture"
    if any(k in t for k in ("معماری", "شهرسازی", "طراحی داخلی", "منظر")):
        return "architecture"
    if any(k in t for k in ("هنر", "موسیقی", "سینما", "نمایش", "عکاسی", "گرافیک")) and "معماری" not in t:
        return "arts"
    if any(
        k in t
        for k in (
            "مهندسی",
            "کامپیوتر",
            "برق",
            "مکانیک",
            "عمران",
            "صنایع",
            "هوش مصنوعی",
            "امنیت سایبری",
            "علوم داده",
            "نرم",
            "فناوری",
            "هوانوردی",
        )
    ):
        return "engineering"
    if any(k in t for k in ("ریاضی", "فیزیک", "شیمی", "آمار", "زیست", "علوم اعصاب", "علوم شناختی", "محیط زیست")):
        return "science"
    return "general"

_LINK_MAJOR_FIELDS = ("id", "title", "slug", "short_description", "country", "image", "order")
_LINK_UNI_FIELDS = (
    "id",
    "slug",
    "name_fa",
    "name_en",
    "city",
    "country",
    "type",
    "image",
    "world_rank",
    "short_description",
    "is_approved_by_mo_science",
    "is_approved_by_mo_health",
)


def _ordered_major_links_qs():
    return (
        UniversityMajorLink.objects.select_related("major")
        .filter(major__is_active=True)
        .only(
            "id",
            "university_id",
            "major_id",
            "is_featured",
            "order",
            *[f"major__{f}" for f in _LINK_MAJOR_FIELDS],
        )
        .order_by("-is_featured", "order", "id")
    )


def _ordered_university_links_qs():
    return (
        UniversityMajorLink.objects.select_related("university")
        .only(
            "id",
            "university_id",
            "major_id",
            "is_featured",
            "order",
            *[f"university__{f}" for f in _LINK_UNI_FIELDS],
        )
        .order_by("-is_featured", "order", "id")
    )


def get_university_linked_majors(university: University, *, limit: int | None = None) -> list[Major]:
    links = list(_ordered_major_links_qs().filter(university_id=university.pk))
    majors = [link.major for link in links]
    if limit is not None:
        return majors[:limit]
    return majors


def get_major_linked_universities_with_count(
    major: Major, *, limit: int | None = None
) -> tuple[list[University], int]:
    """یک بار لینک‌ها را می‌خواند؛ تعداد کل همان len همان لیست است (بدون کوئری اضافه)."""
    links = list(_ordered_university_links_qs().filter(major_id=major.pk))
    total = len(links)
    universities = [link.university for link in links]
    if limit is not None:
        return universities[:limit], total
    return universities, total


def get_major_linked_universities(major: Major, *, limit: int | None = None) -> list[University]:
    universities, _total = get_major_linked_universities_with_count(major, limit=limit)
    return universities


def prefetch_university_major_links(university_qs):
    return university_qs.prefetch_related(
        Prefetch("major_links", queryset=_ordered_major_links_qs())
    )


def prefetch_major_university_links(major_qs):
    return major_qs.prefetch_related(
        Prefetch("university_links", queryset=_ordered_university_links_qs())
    )


def build_majors_list_url_for_university(university: University) -> str:
    """آدرس صفحه رشته‌ها با فیلتر کشور و دانشگاه."""
    from .nav_degrees import append_query_params

    params: dict[str, str] = {"university": university.slug}
    if university.country:
        params["country"] = university.country
    return append_query_params(reverse("majors"), params)


def build_appointment_url(
    *,
    about: str,
    title: str = "",
    country: str = "",
) -> str:
    """لینک رزرو مشاوره با query string استاندارد (urlencode برای فارسی)."""
    from .nav_degrees import append_query_params

    params: dict[str, str] = {"about": about}
    if title:
        params["title"] = title
    if country:
        params["country"] = country
    return append_query_params(reverse("appointment"), params)


def group_majors_preview_by_category(
    majors: list[Major],
    *,
    per_category: int = PREVIEW_MAJORS_PER_CATEGORY,
) -> list[dict]:
    """
    گروه‌بندی رشته‌های لینک‌شده برای پیش‌نمایش صفحه دانشگاه.
    در هر دسته حداکثر per_category رشته (اولویت با is_featured در ترتیب ورودی).
    """
    per_category = max(1, int(per_category or PREVIEW_MAJORS_PER_CATEGORY))
    buckets: dict[str, list[Major]] = {key: [] for key in MAJOR_CATEGORY_ORDER}
    for major in majors:
        cat = classify_major_display_group(major.title)
        if cat not in buckets:
            cat = "general"
        buckets[cat].append(major)

    groups: list[dict] = []
    for cat in MAJOR_CATEGORY_ORDER:
        items = buckets.get(cat) or []
        if not items:
            continue
        groups.append(
            {
                "category": cat,
                "label": MAJOR_CATEGORY_LABELS.get(cat, cat),
                "majors": items[:per_category],
                "total": len(items),
                "more_count": max(0, len(items) - per_category),
            }
        )
    return groups


PREVIEW_UNIVERSITIES_PER_TIER = 4

UNIVERSITY_TIER_ORDER: tuple[str, ...] = ("top10", "top20", "top30", "other")

UNIVERSITY_TIER_LABELS: dict[str, str] = {
    "top10": "دانشگاه‌های برتر (رتبه ۱ تا ۱۰)",
    "top20": "رتبه ۱۱ تا ۲۰",
    "top30": "رتبه ۲۱ تا ۳۰",
    "other": "سایر دانشگاه‌ها",
}


def _university_tier(world_rank: str) -> str:
    try:
        rank = int((world_rank or "").strip())
    except (TypeError, ValueError):
        return "other"
    if rank <= 10:
        return "top10"
    if rank <= 20:
        return "top20"
    if rank <= 30:
        return "top30"
    return "other"


def build_schools_list_url_for_major(major: Major) -> str:
    """صفحه لیست دانشگاه‌ها با فیلتر کشور و رشته."""
    from .nav_degrees import append_query_params

    params: dict[str, str] = {"major": major.slug}
    if major.country:
        params["country"] = major.country
    return append_query_params(reverse("schools_list"), params)


def group_universities_preview_by_tier(
    universities: list[University],
    *,
    per_tier: int = PREVIEW_UNIVERSITIES_PER_TIER,
) -> list[dict]:
    """پیش‌نمایش دانشگاه‌ها در صفحه رشته — چند مورد از هر بازه رتبه."""
    per_tier = max(1, int(per_tier or PREVIEW_UNIVERSITIES_PER_TIER))
    buckets: dict[str, list[University]] = {key: [] for key in UNIVERSITY_TIER_ORDER}
    for uni in universities:
        tier = _university_tier(uni.world_rank)
        buckets.setdefault(tier, buckets["other"]).append(uni)

    groups: list[dict] = []
    for tier in UNIVERSITY_TIER_ORDER:
        items = buckets.get(tier) or []
        if not items:
            continue
        groups.append(
            {
                "tier": tier,
                "label": UNIVERSITY_TIER_LABELS.get(tier, tier),
                "universities": items[:per_tier],
                "total": len(items),
                "more_count": max(0, len(items) - per_tier),
            }
        )
    return groups
