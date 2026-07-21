"""سئو صفحه تعرفه‌ها و ماشین‌حساب."""

from __future__ import annotations

from typing import Any

from django.urls import reverse

from .google_ai_seo import build_pricing_ai_qa_blocks, enrich_schema_graph_for_google_ai
from .models import PricingTariff


def build_pricing_page_seo(
    *,
    request,
    institute_name: str,
    site_url: str,
    tariffs: list[PricingTariff],
) -> dict[str, Any]:
    path = reverse("pricing")
    base = site_url.rstrip("/")
    page_url = f"{base}{path}"

    meta_title = "تعرفه خدمات مهاجرت تحصیلی و ماشین‌حساب هوشمند"
    meta_description = (
        f"تعرفه شفاف خدمات مهاجرت تحصیلی، اپلای دانشگاه، ویزا و گواهی مقرری در {institute_name}. "
        "با ماشین‌حساب هوشمند، خدمات مناسب و برآورد هزینه پرونده خود را ببینید."
    )
    og_title = f"{meta_title} | {institute_name}"

    offers = []
    for t in tariffs[:15]:
        if t.price_type == PricingTariff.PRICE_CONTACT:
            continue
        if t.price_foreign_amount and t.price_foreign_currency:
            offers.append(
                {
                    "@type": "Offer",
                    "name": t.title,
                    "description": (t.short_description or t.description)[:200],
                    "price": str(t.price_foreign_amount),
                    "priceCurrency": t.price_foreign_currency,
                    "url": page_url,
                }
            )
        elif t.allowance_percent:
            offers.append(
                {
                    "@type": "Offer",
                    "name": t.title,
                    "description": (t.short_description or t.description)[:200],
                    "priceSpecification": {
                        "@type": "PriceSpecification",
                        "price": f"حداکثر {t.allowance_percent}٪ مقرری ماهانه",
                    },
                    "url": page_url,
                }
            )

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
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "صفحه اصلی", "item": f"{base}/"},
                {"@type": "ListItem", "position": 2, "name": "تعرفه خدمات", "item": page_url},
            ],
        },
    ]

    if offers:
        graph.append(
            {
                "@type": "Service",
                "@id": f"{page_url}#services",
                "name": "خدمات مهاجرت تحصیلی",
                "provider": {"@type": "EducationalOrganization", "name": institute_name},
                "offers": offers,
            }
        )

    schema = {"@context": "https://schema.org", "@graph": graph}

    ai_qa_blocks = build_pricing_ai_qa_blocks(institute_name)
    pricing_schema_json = enrich_schema_graph_for_google_ai(
        schema,
        site_url=base,
        qa_blocks=ai_qa_blocks,
        speakable_selectors=[".pricing-page__hero-answer", ".ai-qa-section__answer"],
        page_url=page_url,
    )

    return {
        "pricing_meta_title": meta_title,
        "pricing_meta_description": meta_description,
        "pricing_meta_keywords": (
            "تعرفه مهاجرت تحصیلی, هزینه اپلای دانشگاه, ویزای تحصیلی, "
            "گواهی مقرری, تمکن مالی, موسسه اعزام دانشجو"
        ),
        "pricing_page_url": page_url,
        "pricing_schema": schema,
        "pricing_schema_json": pricing_schema_json,
        "pricing_og_title": og_title,
        "pricing_ai_qa_blocks": ai_qa_blocks,
        "pricing_ai_qa_title": "پرسش‌های رایج درباره تعرفه خدمات",
        "pricing_ai_qa_lead": f"پاسخ‌های کوتاه {institute_name} — برای برآورد دقیق از ماشین‌حساب استفاده کنید.",
        "pricing_answer_summary": ai_qa_blocks[0]["short_answer"] if ai_qa_blocks else meta_description,
    }
