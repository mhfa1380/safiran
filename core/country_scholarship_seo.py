"""سئو صفحات بورسیه کشور — متا، canonical و داده ساختاریافته."""

from __future__ import annotations

from typing import Any

from django.urls import reverse

from .google_ai_seo import build_scholarship_ai_qa_blocks, enrich_schema_graph_for_google_ai
from .models import CountryScholarship, CountryScholarshipGuide, StudyCountry


def _resolve_guide(
    country: StudyCountry,
    target_degree: str,
) -> CountryScholarshipGuide | None:
    qs = CountryScholarshipGuide.objects.filter(country=country, is_active=True)
    if target_degree:
        guide = qs.filter(target_degree=target_degree).first()
        if guide:
            return guide
    return qs.filter(target_degree="").first()


def get_country_scholarship_guide(
    country_code: str,
    target_degree: str = "",
) -> CountryScholarshipGuide | None:
    country = StudyCountry.objects.filter(code=country_code, is_active=True).first()
    if not country:
        return None
    degree = (target_degree or "").strip().lower()
    if degree not in ("bachelor", "master", "phd"):
        degree = ""
    return _resolve_guide(country, degree)


def build_country_scholarship_seo(
    *,
    request,
    country: StudyCountry,
    guide: CountryScholarshipGuide,
    scholarships: list[CountryScholarship],
    institute_name: str,
    site_url: str,
    target_degree: str = "",
) -> dict[str, Any]:
    base = (site_url or "").rstrip("/")
    path = reverse("country_scholarships", kwargs={"country_code": country.code})
    if target_degree:
        path += f"?target_degree={target_degree}"
    page_url = f"{base}{path}" if base else request.build_absolute_uri(path)

    meta_title = f"{guide.get_meta_title()} | {institute_name}"
    meta_description = guide.get_meta_description()
    meta_keywords = (guide.meta_keywords or "").strip() or (
        f"بورسیه {country.name}, بورسیه تحصیل {country.name}, "
        f"بورسیه دانشجویان بین‌المللی {country.name}"
    )

    country_path = reverse("country_detail", kwargs={"country_code": country.code})
    country_url = f"{base}{country_path}" if base else request.build_absolute_uri(country_path)

    qa_blocks = build_scholarship_ai_qa_blocks(
        country,
        guide,
        scholarships,
        institute_name=institute_name,
    )
    answer_summary = qa_blocks[0]["short_answer"] if qa_blocks else meta_description[:220]

    graph: list[dict[str, Any]] = [
        {
            "@type": "BreadcrumbList",
            "@id": f"{page_url}#breadcrumb",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "صفحه اصلی", "item": f"{base}/"},
                {"@type": "ListItem", "position": 2, "name": country.name, "item": country_url},
                {"@type": "ListItem", "position": 3, "name": guide.get_meta_title(), "item": page_url},
            ],
        },
        {
            "@type": "WebPage",
            "@id": f"{page_url}#webpage",
            "url": page_url,
            "name": meta_title,
            "description": meta_description,
            "inLanguage": "fa-IR",
            "about": {"@type": "Country", "name": country.name},
            "isPartOf": {"@id": f"{base}/#website"},
            "abstract": answer_summary,
        },
    ]

    if scholarships:
        graph.append(
            {
                "@type": "ItemList",
                "@id": f"{page_url}#scholarships",
                "name": f"بورسیه‌های {country.name}",
                "numberOfItems": len(scholarships),
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": idx + 1,
                        "name": s.name,
                        "description": s.coverage,
                        "url": f"{page_url}#scholarship-{s.slug}",
                    }
                    for idx, s in enumerate(scholarships[:12])
                ],
            }
        )

    schema = {"@context": "https://schema.org", "@graph": graph}
    schema_json = enrich_schema_graph_for_google_ai(
        schema,
        site_url=base,
        qa_blocks=qa_blocks,
        speakable_selectors=[".scholar-page__hero-answer", ".ai-qa-section__answer"],
        page_url=page_url,
    )

    return {
        "scholarship_meta_title": meta_title,
        "scholarship_meta_description": meta_description,
        "scholarship_meta_keywords": meta_keywords,
        "scholarship_page_url": page_url,
        "scholarship_og_title": meta_title,
        "scholarship_schema_json": schema_json,
        "scholarship_ai_qa_blocks": qa_blocks,
        "scholarship_answer_summary": answer_summary,
        "scholarship_ai_qa_title": f"پرسش‌های رایج درباره بورسیه {country.name}",
        "scholarship_ai_qa_lead": (
            f"پاسخ‌های کوتاه {institute_name} — برای جزئیات به کارت‌های بورسیه و راهنمای اپلای مراجعه کنید."
        ),
    }
