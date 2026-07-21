"""سئو و سیگنال Google AI برای صفحه جزئیات دانشگاه."""

from __future__ import annotations

import json
from typing import Any

from django.urls import reverse

from .google_ai_seo import _faq_entities_from_blocks, build_university_ai_qa_blocks
from .schema_utils import country_iso_alpha2


def build_university_page_seo(
    *,
    university,
    university_faqs,
    linked_majors,
    site_url: str,
    canonical_url: str,
    institute_name: str,
) -> dict[str, Any]:
    site = site_url.rstrip("/")
    page = canonical_url.rstrip("/") + "/"
    meta_title = university.meta_title or university.name_fa
    meta_description = (
        university.meta_description
        or university.short_description
        or f"اطلاعات دانشگاه {university.name_fa} — پذیرش، رشته‌ها و مشاوره مهاجرت تحصیلی."
    )

    qa_blocks = build_university_ai_qa_blocks(university, university_faqs)
    answer_summary = qa_blocks[0]["short_answer"] if qa_blocks else meta_description[:200]

    country_iso = country_iso_alpha2(university.country or "")
    image_url = ""
    if university.image:
        image_url = university.image.url
        if not image_url.startswith("http"):
            image_url = f"{site}{image_url}"

    graph: list[dict[str, Any]] = [
        {
            "@type": "BreadcrumbList",
            "@id": f"{page}#breadcrumb",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "صفحه اصلی", "item": f"{site}/"},
                {
                    "@type": "ListItem",
                    "position": 2,
                    "name": "دانشگاه‌ها",
                    "item": f"{site}{reverse('schools_list')}",
                },
                {"@type": "ListItem", "position": 3, "name": university.name_fa, "item": page},
            ],
        },
        {
            "@type": "WebPage",
            "@id": f"{page}#webpage",
            "url": page,
            "name": meta_title,
            "description": meta_description[:320],
            "inLanguage": "fa-IR",
            "isPartOf": {"@id": f"{site}/#website"},
            "publisher": {"@id": f"{site}/#organization"},
            "speakable": {
                "@type": "SpeakableSpecification",
                "cssSelector": [".school-detail__hero-answer", ".ai-qa-section__answer"],
            },
            "abstract": answer_summary,
        },
        {
            "@type": "CollegeOrUniversity",
            "@id": f"{page}#university",
            "name": university.name_en or university.name_fa,
            "alternateName": university.name_fa,
            "description": (university.short_description or "")[:320],
            "url": page,
            "address": {
                "@type": "PostalAddress",
                "addressLocality": university.city or "",
                "addressCountry": country_iso,
            },
        },
    ]
    if image_url:
        graph[-1]["image"] = image_url
    if university.website:
        graph[-1]["sameAs"] = university.website

    if linked_majors:
        graph.append(
            {
                "@type": "ItemList",
                "@id": f"{page}#majors",
                "name": f"رشته‌های {university.name_fa}",
                "numberOfItems": len(linked_majors),
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": idx,
                        "url": f"{site}{reverse('major_details', kwargs={'slug': major.slug})}",
                        "name": major.title,
                    }
                    for idx, major in enumerate(linked_majors[:20], start=1)
                ],
            }
        )

    faq_entities = _faq_entities_from_blocks(qa_blocks)
    if faq_entities:
        graph.append(
            {
                "@type": "FAQPage",
                "@id": f"{page}#faq",
                "url": page,
                "mainEntity": faq_entities,
            }
        )

    schema = {"@context": "https://schema.org", "@graph": graph}

    return {
        "university_ai_qa_blocks": qa_blocks,
        "university_answer_summary": answer_summary,
        "university_schema_json": json.dumps(schema, ensure_ascii=False),
        "university_ai_qa_title": f"پرسش‌های رایج درباره {university.name_fa}",
        "university_ai_qa_lead": f"پاسخ‌های کوتاه {institute_name} — برای جزئیات بیشتر به بخش‌های زیر مراجعه کنید.",
    }
