"""
عبارت‌های جستجوی ویکی‌پدیا برای تصویر کاور دانشگاه‌ها.
"""
from __future__ import annotations

from core.study_destinations import WORLD_STUDY_COUNTRY_LABELS

COUNTRY_SEARCH_CONTEXT: dict[str, str] = {
    "canada": "Canada",
    "usa": "United States",
    "uk": "United Kingdom",
    "china": "China",
    "spain": "Spain",
    "germany": "Germany",
    "france": "France",
    "australia": "Australia",
    "italy": "Italy",
    "netherlands": "Netherlands",
    "japan": "Japan",
    "south_korea": "South Korea",
    "turkey": "Turkey",
    "uae": "United Arab Emirates",
}


def _country_label(country_code: str) -> str:
    code = (country_code or "").strip().lower()
    if code in COUNTRY_SEARCH_CONTEXT:
        return COUNTRY_SEARCH_CONTEXT[code]
    if code in WORLD_STUDY_COUNTRY_LABELS:
        return WORLD_STUDY_COUNTRY_LABELS[code]
    return code.replace("_", " ").title()


def build_university_wikipedia_queries(
    name_en: str,
    *,
    country: str = "",
    city: str = "",
    name_fa: str = "",
) -> list[str]:
    """لیست مرتب‌شده عبارت‌های جستجو — از دقیق‌ترین به عمومی‌ترین."""
    name = (name_en or "").strip()
    country = (country or "").strip().lower()
    local_name = (name_fa or "").strip()

    if country == "china" and local_name:
        queries: list[str] = [local_name]
        if "大学" not in local_name:
            queries.append(f"{local_name}大学")
        queries.append(f"{local_name} 校园")
        if name:
            queries.append(name)
            if "university" not in name.lower():
                queries.append(f"{name} university")
            queries.append(f"{name} campus")
    elif not name:
        return []
    else:
        queries = [name]
        low = name.lower()
        has_uni_word = any(w in low for w in ("university", "college", "institut", "polytechnic", "école"))
        if not has_uni_word:
            queries.append(f"{name} university")

    country_label = _country_label(country)
    city = (city or "").strip()
    low = name.lower() if name else ""
    has_uni_word = any(w in low for w in ("university", "college", "institut", "polytechnic", "école"))

    if city and name and city.lower() not in low:
        queries.append(f"{name} {city}")
        if not has_uni_word:
            queries.append(f"{name} university {city}")

    if country_label and name:
        queries.append(f"{name} {country_label}")
        if not has_uni_word:
            queries.append(f"{name} university {country_label}")

    if country == "spain" and local_name and local_name != name:
        queries.insert(0, local_name)
        if "universidad" not in local_name.lower():
            queries.insert(1, f"Universidad {local_name}")

    # حذف تکراری با حفظ ترتیب
    seen: set[str] = set()
    unique: list[str] = []
    for q in queries:
        key = q.casefold()
        if key not in seen:
            seen.add(key)
            unique.append(q)
    return unique
