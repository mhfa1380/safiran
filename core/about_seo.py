"""سئو و سیگنال Google AI برای صفحه درباره ما."""

from __future__ import annotations

from typing import Any

from .google_ai_seo import (
    build_about_ai_qa_blocks,
    build_index_answer_summary,
    enrich_schema_graph_for_google_ai,
)


def build_about_page_seo(
    *,
    institute,
    site_url: str,
    canonical_url: str,
) -> dict[str, Any]:
    site = site_url.rstrip("/")
    page = canonical_url.rstrip("/") + "/"
    institute_name = getattr(institute, "name", "") or "موسسه"
    answer_summary = build_index_answer_summary(institute)
    meta_title = f"درباره موسسه مهاجرت تحصیلی {institute_name}"
    meta_description = (
        f"آشنایی با موسسه مهاجرت تحصیلی {institute_name}؛ داستان برند، تیم مشاوران "
        "و اعزام دانشجو با مجوز رسمی وزارت علوم."
    )

    qa_blocks = build_about_ai_qa_blocks(institute)

    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "BreadcrumbList",
                "@id": f"{page}#breadcrumb",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "صفحه اصلی", "item": f"{site}/"},
                    {"@type": "ListItem", "position": 2, "name": "درباره ما", "item": page},
                ],
            },
            {
                "@type": "WebPage",
                "@id": f"{page}#webpage",
                "url": page,
                "name": meta_title,
                "description": meta_description,
                "inLanguage": "fa-IR",
                "about": {"@id": f"{site}/#organization"},
                "isPartOf": {"@id": f"{site}/#website"},
                "publisher": {"@id": f"{site}/#organization"},
                "speakable": {
                    "@type": "SpeakableSpecification",
                    "cssSelector": [".about-page__hero-answer", ".ai-qa-section__answer"],
                },
                "abstract": answer_summary,
            },
            {
                "@type": "AboutPage",
                "@id": f"{page}#about",
                "url": page,
                "name": meta_title,
                "description": answer_summary,
                "mainEntity": {"@id": f"{site}/#organization"},
            },
        ],
    }

    schema_json = enrich_schema_graph_for_google_ai(
        schema,
        site_url=site,
        qa_blocks=qa_blocks,
        speakable_selectors=[".about-page__hero-answer", ".ai-qa-section__answer"],
        page_url=page,
    )

    return {
        "about_ai_qa_blocks": qa_blocks,
        "about_answer_summary": answer_summary,
        "about_schema_json": schema_json,
        "about_ai_qa_title": f"پرسش‌های رایج درباره {institute_name}",
        "about_ai_qa_lead": "پاسخ‌های کوتاه رسمی موسسه — برای جزئیات بیشتر به بخش‌های صفحه مراجعه کنید.",
    }
