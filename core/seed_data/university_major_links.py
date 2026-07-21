"""
تخصیص رشته‌های مرتبط به هر دانشگاه — بر اساس پروفایل دانشگاه و رتبه ملی.

هر دانشگاه فقط رشته‌های همان کشور را می‌گیرد؛ تعداد و نوع رشته بسته به
قدرت دانشگاه (رتبه، تأیید بهداشت، پروفایل تخصصی) تعیین می‌شود.
"""
from __future__ import annotations

from core.seed_data.major_catalog import get_majors_for_country
from core.university_majors import MAJOR_CATEGORY_ORDER, classify_major_display_group

# پروفایل تخصصی برخی دانشگاه‌ها (slug → دسته‌های رشته)
UNIVERSITY_SLUG_PROFILES: dict[str, dict[str, tuple[str, ...]]] = {
    "canada": {
        "university-of-waterloo": ("engineering", "science", "business", "general"),
        "university-of-toronto": ("medical", "engineering", "business", "science", "arts", "law", "general"),
        "mcgill-university": ("medical", "engineering", "business", "science", "arts", "law", "general"),
        "university-of-british-columbia": ("medical", "engineering", "business", "science", "arts", "general"),
        "university-of-alberta": ("medical", "engineering", "business", "science", "agriculture", "general"),
        "universite-de-montreal": ("medical", "engineering", "science", "arts", "general"),
        "toronto-metropolitan-university": ("business", "engineering", "arts", "general"),
        "acadia-university": ("business", "education", "science", "general"),
    },
    "spain": {
        "ie-university": ("business", "law", "general"),
        "upc-barcelona-tech": ("engineering", "science", "general"),
        "universidad-politecnica-de-madrid": ("engineering", "science", "architecture", "general"),
        "universidad-de-navarra": ("medical", "business", "law", "general"),
        "universitat-pompeu-fabra": ("business", "science", "arts", "general"),
        "universidad-carlos-iii-madrid": ("business", "engineering", "law", "general"),
        "universidad-complutense-madrid": ("medical", "arts", "science", "law", "general"),
        "universitat-de-barcelona": ("medical", "science", "arts", "general"),
    },
    "china": {
        "beijing-institute-of-technology": ("engineering", "science", "general"),
        "beihang-university": ("engineering", "science", "general"),
        "harbin-institute-of-technology": ("engineering", "science", "general"),
        "dalian-university-of-technology": ("engineering", "science", "general"),
        "southeast-university-china": ("engineering", "medical", "architecture", "general"),
        "peking-university": ("medical", "engineering", "business", "science", "arts", "law", "general"),
        "tsinghua-university": ("engineering", "business", "science", "architecture", "general"),
        "fudan-university": ("medical", "business", "science", "arts", "general"),
        "china-agricultural-university": ("agriculture", "science", "medical", "general"),
        "east-china-normal-university": ("education", "science", "language", "general"),
    },
}

_CATEGORY_EXPAND: dict[str, tuple[str, ...]] = {
    "architecture": ("معماری", "شهرسازی", "طراحی"),
}

# رشته‌هایی که در هر کشور اولویت نمایش دارند
_COUNTRY_PRIORITY_SNIPPETS: dict[str, tuple[str, ...]] = {
    "canada": (
        "مهندسی",
        "MBA",
        "علوم داده",
        "هوش مصنوعی",
        "پزشکی",
        "مدیریت",
        "حسابداری",
        "حقوق",
        "روان‌شناسی",
    ),
    "spain": (
        "MBA",
        "گردشگری",
        "هتلداری",
        "مهندسی",
        "حقوق",
        "معماری",
        "پزشکی",
    ),
    "china": (
        "پزشکی عمومی",
        "دندانپزشکی",
        "مهندسی",
        "MBA",
        "علوم داده",
        "زبان چینی",
        "هوش مصنوعی",
    ),
}

_DEFAULT_PRIORITY = (
    "مهندسی",
    "MBA",
    "علوم داده",
    "هوش مصنوعی",
    "پزشکی",
    "مدیریت",
    "حسابداری",
    "حقوق",
    "روان‌شناسی",
)


def _major_matches_categories(title: str, categories: tuple[str, ...]) -> bool:
    cat = classify_major_display_group(title)
    if cat in categories:
        return True
    for group in categories:
        for kw in _CATEGORY_EXPAND.get(group, ()):
            if kw in title:
                return True
    return False


def _default_categories(item: dict) -> tuple[str, ...]:
    rank = int(item.get("world_rank") or 99)
    if item.get("mo_health"):
        if rank <= 10:
            return ("medical", "science", "engineering", "general")
        return ("medical", "science", "general")
    if rank <= 5:
        return ("engineering", "business", "science", "medical", "arts", "law", "general")
    if rank <= 15:
        return ("engineering", "business", "science", "arts", "general")
    return ("engineering", "business", "science", "general")


def _major_limit(item: dict) -> int:
    rank = int(item.get("world_rank") or 99)
    if rank <= 5:
        return 32
    if rank <= 10:
        return 28
    if rank <= 20:
        return 24
    return 20


def _sort_key(country_code: str, title: str) -> tuple[int, int, str]:
    priority = _COUNTRY_PRIORITY_SNIPPETS.get(country_code, _DEFAULT_PRIORITY)
    pri = 0
    for i, snippet in enumerate(priority):
        if snippet in title:
            pri = -(len(priority) - i)
            break
    return (pri, 0 if classify_major_display_group(title) == "engineering" else 1, title)


def _select_balanced_major_titles(
    matched: list[str],
    country_code: str,
    *,
    limit: int,
) -> list[str]:
    """از هر دسته چند رشته برتر — تا لیست مهندسی‌محور یک‌طرفه نشود."""
    if not matched or limit <= 0:
        return []
    buckets: dict[str, list[str]] = {}
    for title in matched:
        cat = classify_major_display_group(title)
        buckets.setdefault(cat, []).append(title)
    for cat in buckets:
        buckets[cat].sort(key=lambda t: _sort_key(country_code, t))

    active_cats = [c for c in MAJOR_CATEGORY_ORDER if c in buckets]
    if not active_cats:
        return matched[:limit]

    per_cat = max(2, (limit + len(active_cats) - 1) // len(active_cats))
    selected: list[str] = []
    seen: set[str] = set()
    for cat in active_cats:
        for title in buckets[cat][:per_cat]:
            if title in seen:
                continue
            seen.add(title)
            selected.append(title)
            if len(selected) >= limit:
                return selected

    for title in sorted(matched, key=lambda t: _sort_key(country_code, t)):
        if title in seen:
            continue
        seen.add(title)
        selected.append(title)
        if len(selected) >= limit:
            break
    return selected


def get_major_titles_for_university(item: dict, country_code: str) -> list[str]:
    """رشته‌های مرتبط با یک دانشگاه — بدون تکرار، مرتب‌شده برای نمایش."""
    all_titles = get_majors_for_country(country_code)
    slug = item.get("slug", "")
    profiles = UNIVERSITY_SLUG_PROFILES.get(country_code, {}).get(slug)
    categories = profiles if profiles else _default_categories(item)
    matched = [t for t in all_titles if _major_matches_categories(t, categories)]
    if not matched:
        matched = list(all_titles)
    limit = _major_limit(item)
    return _select_balanced_major_titles(matched, country_code, limit=limit)
