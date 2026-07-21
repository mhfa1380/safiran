"""سئو صفحه خدمات موسسه — متا، canonical و داده ساختاریافته."""

from __future__ import annotations

import re
from typing import Any, Optional

from django.urls import reverse

from .faq_seo import _plain_answer
from .google_ai_seo import build_services_ai_qa_blocks, enrich_schema_graph_for_google_ai
from .models import Service, ServiceCategory


def _plain_text(html: str, *, max_len: int = 500) -> str:
    return _plain_answer(html, max_len=max_len)


def _absolute_url_from_site(site_url: str, path: str) -> str:
    return f"{site_url.rstrip('/')}{path}"


def _default_meta(*, institute_name: str, category: Optional[ServiceCategory]) -> tuple[str, str]:
    if category:
        return category.get_meta_title(), category.get_meta_description()

    title = "خدمات با ما — مهاجرت تحصیلی و اعزام دانشجو"
    description = (
        f"خدمات کامل {institute_name} از مشاوره و ارزیابی تا پذیرش دانشگاه، ویزای تحصیلی، "
        f"بورسیه و استقرار در کشور مقصد — همراهی تخصصی برای دانشجویان ایرانی."
    )
    return title, description


def _meta_keywords(
    category: Optional[ServiceCategory],
    categories: list[ServiceCategory],
) -> str:
    base = [
        "خدمات موسسه",
        "خدمات با ما",
        "مهاجرت تحصیلی",
        "اعزام دانشجو",
        "مشاوره مهاجرت",
        "پذیرش دانشگاه",
        "ویزای تحصیلی",
        "بورسیه تحصیلی",
    ]
    if category:
        base.insert(0, category.name)
    else:
        for cat in categories[:6]:
            if cat.name and cat.name not in base:
                base.append(cat.name)
    return ", ".join(base)


def _breadcrumb_schema(
    *,
    site_url: str,
    page_url: str,
    category: Optional[ServiceCategory],
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = [
        {
            "@type": "ListItem",
            "position": 1,
            "name": "صفحه اصلی",
            "item": f"{site_url.rstrip('/')}/",
        },
        {
            "@type": "ListItem",
            "position": 2,
            "name": "خدمات با ما",
            "item": page_url if category else _absolute_url_from_site(site_url, reverse("services")),
        },
    ]
    if category:
        items.append(
            {
                "@type": "ListItem",
                "position": 3,
                "name": category.name,
                "item": page_url,
            }
        )
    return items


def build_services_schema(
    *,
    site_url: str,
    page_url: str,
    page_title: str,
    page_description: str,
    institute_name: str,
    services: list[Service],
    category: Optional[ServiceCategory],
    categories: list[ServiceCategory],
) -> dict[str, Any]:
    site_url = site_url.rstrip("/")
    page_url = page_url.rstrip("/") + ("/" if not page_url.endswith("/") else "")

    graph: list[dict[str, Any]] = [
        {
            "@type": "WebPage",
            "@id": f"{page_url}#webpage",
            "url": page_url,
            "name": page_title,
            "description": page_description,
            "inLanguage": "fa-IR",
            "isPartOf": {
                "@type": "WebSite",
                "@id": f"{site_url}/#website",
                "name": institute_name,
                "url": f"{site_url}/",
            },
        }
    ]

    service_items: list[dict[str, Any]] = []
    for idx, service in enumerate(services, start=1):
        summary = _plain_text(service.get_display_summary())
        if not summary:
            continue
        entry: dict[str, Any] = {
            "@type": "ListItem",
            "position": idx,
            "name": service.title,
            "description": summary,
        }
        if service.slug:
            entry["url"] = f"{page_url}#service-{service.slug}"
        service_items.append(entry)

    if service_items:
        graph.append(
            {
                "@type": "ItemList",
                "@id": f"{page_url}#services",
                "name": "خدمات موسسه",
                "itemListElement": service_items,
            }
        )

    graph.append(
        {
            "@type": "BreadcrumbList",
            "@id": f"{page_url}#breadcrumb",
            "itemListElement": _breadcrumb_schema(
                site_url=site_url,
                page_url=page_url,
                category=category,
            ),
        }
    )

    if not category and categories:
        graph.append(
            {
                "@type": "ItemList",
                "@id": f"{page_url}#categories",
                "name": "دسته‌بندی خدمات",
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": idx,
                        "name": cat.name,
                        "url": _absolute_url_from_site(
                            site_url,
                            reverse("services_category", kwargs={"category_slug": cat.slug}),
                        ),
                    }
                    for idx, cat in enumerate(categories, start=1)
                ],
            }
        )

    return {"@context": "https://schema.org", "@graph": graph}


def build_services_page_seo(
    *,
    request,
    institute_name: str,
    active_category: Optional[ServiceCategory],
    categories: list[ServiceCategory],
    services: list[Service],
    site_url: str,
) -> dict[str, Any]:
    meta_title, meta_description = _default_meta(
        institute_name=institute_name,
        category=active_category,
    )

    if active_category:
        page_path = reverse("services_category", kwargs={"category_slug": active_category.slug})
    else:
        page_path = reverse("services")

    page_url = _absolute_url_from_site(site_url, page_path)
    og_title = f"{meta_title} | {institute_name}"

    schema = build_services_schema(
        site_url=site_url,
        page_url=page_url,
        page_title=meta_title,
        page_description=meta_description,
        institute_name=institute_name,
        services=services,
        category=active_category,
        categories=categories,
    )

    ai_qa_blocks = build_services_ai_qa_blocks(
        institute_name=institute_name,
        category=active_category,
        services=services,
        categories=categories,
    )
    schema_json = enrich_schema_graph_for_google_ai(
        schema,
        site_url=site_url,
        qa_blocks=ai_qa_blocks,
        speakable_selectors=[".services-page__hero-answer", ".ai-qa-section__answer"],
        page_url=page_url,
    )

    if active_category:
        ai_qa_title = f"پرسش‌های رایج درباره خدمات {active_category.name}"
    else:
        ai_qa_title = f"پرسش‌های رایج درباره خدمات {institute_name}"

    return {
        "services_meta_title": meta_title,
        "services_meta_description": meta_description,
        "services_meta_keywords": _meta_keywords(active_category, categories),
        "services_page_url": page_url,
        "services_og_title": og_title,
        "services_schema": schema,
        "services_schema_json": schema_json,
        "services_ai_qa_blocks": ai_qa_blocks,
        "services_ai_qa_title": ai_qa_title,
        "services_ai_qa_lead": f"پاسخ‌های کوتاه {institute_name} — برای جزئیات هر خدمت به کارت‌های زیر مراجعه کنید.",
        "services_answer_summary": ai_qa_blocks[0]["short_answer"] if ai_qa_blocks else meta_description,
    }
