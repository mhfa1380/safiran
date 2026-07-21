"""سئو صفحه دستاوردهای ما."""

from __future__ import annotations

import json
import re
from typing import Any

from django.urls import reverse

from .faq_seo import _plain_answer
from .models import MonthlyAchievement


def build_achievements_page_seo(
    *,
    request,
    institute_name: str,
    site_url: str,
    achievements: list[MonthlyAchievement],
) -> dict[str, Any]:
    path = reverse("monthly_achievements")
    base = site_url.rstrip("/")
    page_url = f"{base}{path}"

    meta_title = "دستاوردهای ما و داستان موفقیت دانشجویان"
    meta_description = (
        f"داستان موفقیت و دستاوردهای دانشجویان {institute_name} در مهاجرت تحصیلی؛ "
        "مصاحبه، ویدیو و تجربه واقعی پذیرش و ویزای تحصیلی."
    )
    og_title = f"{meta_title} | {institute_name}"

    items_schema = []
    for idx, item in enumerate(achievements[:20], start=1):
        detail_path = reverse("achievement_detail", kwargs={"achievement_slug": item.slug})
        detail_url = f"{base}{detail_path}"
        entry: dict[str, Any] = {
            "@type": "ListItem",
            "position": idx,
            "name": item.title,
            "description": item.description[:200] if item.description else item.person_name,
            "url": detail_url,
        }
        if item.image:
            entry["image"] = request.build_absolute_uri(item.image.url)
        items_schema.append(entry)

    graph: list[dict[str, Any]] = [
        {
            "@type": "WebPage",
            "@id": f"{page_url}#webpage",
            "url": page_url,
            "name": meta_title,
            "description": meta_description,
            "inLanguage": "fa-IR",
            "isPartOf": {
                "@type": "WebSite",
                "@id": f"{base}/#website",
                "name": institute_name,
                "url": f"{base}/",
            },
        },
        {
            "@type": "CollectionPage",
            "@id": f"{page_url}#collection",
            "url": page_url,
            "name": meta_title,
            "description": meta_description,
        },
    ]

    if items_schema:
        graph.append(
            {
                "@type": "ItemList",
                "@id": f"{page_url}#achievements",
                "name": "دستاوردهای ما",
                "itemListElement": items_schema,
            }
        )

    graph.append(
        {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": 1,
                    "name": "صفحه اصلی",
                    "item": f"{base}/",
                },
                {
                    "@type": "ListItem",
                    "position": 2,
                    "name": "دستاوردهای ما",
                    "item": page_url,
                },
            ],
        }
    )

    schema = {"@context": "https://schema.org", "@graph": graph}

    return {
        "achievements_meta_title": meta_title,
        "achievements_meta_description": meta_description,
        "achievements_meta_keywords": (
            "دستاوردهای ما, داستان موفقیت, مهاجرت تحصیلی, اعزام دانشجو, "
            "تجربه دانشجویان, پذیرش دانشگاه"
        ),
        "achievements_page_url": page_url,
        "achievements_schema": schema,
        "achievements_schema_json": json.dumps(schema, ensure_ascii=False),
        "achievements_og_title": og_title,
    }


def _absolute_url(request, path: str, site_url: str) -> str:
    base = site_url.rstrip("/")
    if path.startswith("http"):
        return path
    return f"{base}{path}"


def build_achievement_detail_page_seo(
    *,
    request,
    achievement: MonthlyAchievement,
    institute_name: str,
    site_url: str,
) -> dict[str, Any]:
    path = reverse("achievement_detail", kwargs={"achievement_slug": achievement.slug})
    page_url = _absolute_url(request, path, site_url).rstrip("/") + "/"

    meta_title = achievement.get_meta_title()
    meta_description = achievement.get_meta_description()
    og_title = f"{meta_title} | {institute_name}" if institute_name else meta_title

    body_text = _plain_answer(achievement.get_detail_html())
    image_url = ""
    if achievement.image:
        image_url = request.build_absolute_uri(achievement.image.url)

    graph: list[dict[str, Any]] = [
        {
            "@type": "WebPage",
            "@id": f"{page_url}#webpage",
            "url": page_url,
            "name": meta_title,
            "description": meta_description,
            "inLanguage": "fa-IR",
            "isPartOf": {
                "@type": "WebSite",
                "@id": f"{site_url.rstrip('/')}/#website",
                "name": institute_name,
                "url": f"{site_url.rstrip('/')}/",
            },
        },
        {
            "@type": "Article",
            "@id": f"{page_url}#article",
            "headline": achievement.title,
            "description": meta_description,
            "articleBody": body_text[:5000] if body_text else meta_description,
            "author": {"@type": "Person", "name": achievement.person_name},
            "publisher": {
                "@type": "Organization",
                "name": institute_name,
                "url": f"{site_url.rstrip('/')}/",
            },
            "inLanguage": "fa-IR",
            "url": page_url,
        },
        {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": 1,
                    "name": "صفحه اصلی",
                    "item": f"{site_url.rstrip('/')}/",
                },
                {
                    "@type": "ListItem",
                    "position": 2,
                    "name": "دستاوردهای ما",
                    "item": _absolute_url(request, reverse("monthly_achievements"), site_url),
                },
                {
                    "@type": "ListItem",
                    "position": 3,
                    "name": achievement.person_name,
                    "item": page_url,
                },
            ],
        },
    ]

    if image_url:
        graph[1]["image"] = image_url

    schema = {"@context": "https://schema.org", "@graph": graph}
    keywords = achievement.get_keywords_list()
    if achievement.person_role and achievement.person_role not in keywords:
        keywords = [achievement.person_role, *keywords]

    return {
        "achievement_meta_title": meta_title,
        "achievement_meta_description": meta_description,
        "achievement_meta_keywords": ", ".join(
            ["دستاوردهای ما", "داستان موفقیت", "مهاجرت تحصیلی", *keywords[:8]]
        ),
        "achievement_page_url": page_url,
        "achievement_schema_json": json.dumps(schema, ensure_ascii=False),
        "achievement_og_title": og_title,
    }
