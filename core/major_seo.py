"""سئو و سیگنال Google AI برای صفحه جزئیات رشته."""

from __future__ import annotations

import json
from typing import Any

from django.urls import reverse

from .google_ai_seo import (
    _faq_entities_from_blocks,
    build_major_ai_qa_blocks,
)


def build_major_page_seo(
    *,
    major,
    major_faqs,
    linked_universities,
    linked_universities_count: int,
    site_url: str,
    canonical_url: str,
    institute_name: str,
) -> dict[str, Any]:
    site = site_url.rstrip("/")
    page = canonical_url.rstrip("/") + "/"
    meta_title = major.meta_title or major.get_meta_title()
    meta_description = major.get_meta_description()

    qa_blocks = build_major_ai_qa_blocks(major, major_faqs)
    answer_summary = qa_blocks[0]["short_answer"] if qa_blocks else meta_description

    graph: list[dict[str, Any]] = [
        {
            "@type": "BreadcrumbList",
            "@id": f"{page}#breadcrumb",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "صفحه اصلی", "item": f"{site}/"},
                {
                    "@type": "ListItem",
                    "position": 2,
                    "name": "رشته‌ها",
                    "item": f"{site}{reverse('majors')}",
                },
                {"@type": "ListItem", "position": 3, "name": major.title, "item": page},
            ],
        },
        {
            "@type": "WebPage",
            "@id": f"{page}#webpage",
            "url": page,
            "name": meta_title,
            "description": meta_description,
            "inLanguage": "fa-IR",
            "isPartOf": {"@id": f"{site}/#website"},
            "publisher": {"@id": f"{site}/#organization"},
            "speakable": {
                "@type": "SpeakableSpecification",
                "cssSelector": [".major-detail__hero-answer", ".ai-qa-section__answer"],
            },
            "abstract": answer_summary,
        },
        {
            "@type": "EducationalOccupationalProgram",
            "@id": f"{page}#program",
            "name": meta_title,
            "description": meta_description,
            "url": page,
            "provider": {"@type": "Organization", "name": institute_name},
        },
    ]

    if linked_universities_count and linked_universities:
        graph.append(
            {
                "@type": "ItemList",
                "@id": f"{page}#universities",
                "name": f"دانشگاه‌های {major.title}",
                "numberOfItems": linked_universities_count,
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": idx,
                        "url": f"{site}{reverse('school_detail', kwargs={'slug': uni.slug})}",
                        "name": uni.name_fa,
                    }
                    for idx, uni in enumerate(linked_universities[:20], start=1)
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
        "major_ai_qa_blocks": qa_blocks,
        "major_answer_summary": answer_summary,
        "major_schema_json": json.dumps(schema, ensure_ascii=False),
        "major_ai_qa_title": f"پرسش‌های رایج درباره رشته {major.title}",
        "major_ai_qa_lead": f"پاسخ‌های کوتاه {institute_name} — برای جزئیات بیشتر به بخش‌های زیر مراجعه کنید.",
    }
