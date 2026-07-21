"""سئو صفحات کشور مقصد — متا، canonical و داده ساختاریافته."""

from __future__ import annotations

from typing import Any

from django.urls import reverse

from .google_ai_seo import build_country_ai_qa_blocks, build_country_schema_json
from .models import StudyCountry


def build_country_page_seo(
    *,
    request,
    country: StudyCountry,
    institute_name: str,
    site_url: str,
) -> dict[str, Any]:
    base = (site_url or "").rstrip("/")
    path = reverse("country_detail", kwargs={"country_code": country.code})
    page_url = f"{base}{path}" if base else request.build_absolute_uri(path)

    meta_title = f"{country.get_meta_title()} | {institute_name}"
    meta_description = country.get_meta_description()
    meta_keywords = (country.meta_keywords or "").strip() or (
        f"تحصیل در {country.name}, اعزام دانشجو {country.name}, "
        f"دانشگاه های {country.name}, ویزای تحصیلی {country.name}"
    )

    qa_blocks = build_country_ai_qa_blocks(country)
    qa_questions = {b["anchor_tpl"]: b["question"] for b in qa_blocks if b.get("anchor_tpl")}
    answer_summary = qa_blocks[0]["short_answer"] if qa_blocks else meta_description[:220]

    schema_json = build_country_schema_json(
        country=country,
        page_url=page_url,
        institute_name=institute_name,
        site_url=base,
        meta_title=meta_title,
        meta_description=meta_description,
        qa_blocks=qa_blocks,
    )

    return {
        "country_meta_title": meta_title,
        "country_meta_description": meta_description,
        "country_meta_keywords": meta_keywords,
        "country_page_url": page_url,
        "country_og_title": meta_title,
        "country_schema_json": schema_json,
        "country_ai_qa_blocks": qa_blocks,
        "country_answer_summary": answer_summary,
        "country_guide_questions": qa_questions,
        "country_qa_by_anchor": {b["anchor_tpl"]: b for b in qa_blocks if b.get("anchor_tpl")},
    }
