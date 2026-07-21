"""
کاتالوگ محتوای غنی کشورهای جهانی — برای صفحات StudyCountry.
"""

from __future__ import annotations

from core.study_destinations import PRIMARY_STUDY_COUNTRY_CODES, WORLD_STUDY_COUNTRY_CODES

from .world_rich_country_builder import build_catalog_entry
from .world_rich_country_facts import all_world_country_facts


def build_world_study_country_catalog() -> list[dict]:
    """همه کشورهای جهانی به‌جز سه کشور اصلی که کاتالوگ کامل دارند."""
    items: list[dict] = []
    order = 10
    for facts in all_world_country_facts():
        code = facts["code"]
        if code in PRIMARY_STUDY_COUNTRY_CODES:
            continue
        items.append(build_catalog_entry(facts, order=order))
        order += 1
    return items


WORLD_STUDY_COUNTRY_CODES_LIST = [item["code"] for item in build_world_study_country_catalog()]
