"""
ادغام کاتالوگ دستی (۳۰ برتر) با فهرست گسترده ویکی‌پدیا — بدون تکرار slug.
"""
from __future__ import annotations

from core.seed_data.university_catalog import UNIVERSITY_CATALOG_BY_COUNTRY
from core.seed_data.wikipedia_university_fetcher import build_catalog_entries

_MERGED_CACHE: dict[str, list[dict]] | None = None


def get_merged_university_catalog(
    country_code: str,
    *,
    include_wikipedia: bool = True,
    refresh_wikipedia: bool = False,
) -> list[dict]:
    """کاتالوگ نهایی: ابتدا ۳۰ برتر دستی، سپس بقیه از ویکی‌پدیا."""
    primary = list(UNIVERSITY_CATALOG_BY_COUNTRY.get(country_code, []))
    if not include_wikipedia:
        return primary

    existing_slugs = {item["slug"] for item in primary}
    existing_names = {item["name_en"].lower() for item in primary}

    extra = build_catalog_entries(
        country_code,
        existing_slugs=existing_slugs,
        start_rank=len(primary) + 1,
        use_cache=not refresh_wikipedia,
    )
    merged = list(primary)
    for item in extra:
        if item["name_en"].lower() in existing_names:
            continue
        merged.append(item)
        existing_names.add(item["name_en"].lower())
    return merged


def get_all_merged_catalogs(
    *,
    include_wikipedia: bool = True,
    refresh_wikipedia: bool = False,
) -> dict[str, list[dict]]:
    global _MERGED_CACHE
    if _MERGED_CACHE is not None and include_wikipedia and not refresh_wikipedia:
        return _MERGED_CACHE

    result = {}
    for code in UNIVERSITY_CATALOG_BY_COUNTRY:
        result[code] = get_merged_university_catalog(
            code,
            include_wikipedia=include_wikipedia,
            refresh_wikipedia=refresh_wikipedia,
        )
    if include_wikipedia and not refresh_wikipedia:
        _MERGED_CACHE = result
    return result


def clear_merged_catalog_cache() -> None:
    global _MERGED_CACHE
    _MERGED_CACHE = None
