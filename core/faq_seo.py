"""سئو صفحات سوالات متداول — متا، canonical و داده ساختاریافته."""

from __future__ import annotations

import json
import re
from html import unescape
from typing import Any, Optional

from django.urls import reverse
from django.utils.html import strip_tags

from .models import FAQ, FAQCategory

_BLOCK_END_RE = re.compile(
    r"</(?:p|div|h[1-6]|li|tr|td|th|blockquote|figcaption|dt|dd|section|article|header|footer|thead|tbody|tfoot)\s*>",
    re.I,
)
_BR_RE = re.compile(r"<br\s*/?>", re.I)
_FIRST_P_RE = re.compile(r"<p[^>]*>(.*?)</p>", re.I | re.S)
_LI_RE = re.compile(r"<li[^>]*>(.*?)</li>", re.I | re.S)


def _html_blocks_to_spaces(html: str) -> str:
    """Before strip_tags, insert spaces at block boundaries so cells/headings do not glue."""
    text = _BR_RE.sub(" ", html or "")
    return _BLOCK_END_RE.sub(" ", text)


def _plain_answer(html: str, *, max_len: int = 8000) -> str:
    text = unescape(strip_tags(_html_blocks_to_spaces(html)))
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_len:
        return text[: max_len - 1].rstrip() + "…"
    return text


def _teaser_plain_from_html(html: str) -> str:
    """
    Readable teaser from rich HTML — prefers ordered steps, intro paragraph,
    or fee bullets after tables; never flattens table rows into one line.
    """
    src = html or ""
    before_table = re.split(r"<table\b", src, maxsplit=1, flags=re.I)[0]

    ol_match = re.search(r"<ol[^>]*>(.*?)</ol>", before_table, re.I | re.S)
    if ol_match:
        items = _LI_RE.findall(ol_match.group(1))
        parts = [_plain_answer(item, max_len=220) for item in items[:3]]
        parts = [p for p in parts if p]
        if parts:
            return "؛ ".join(parts)

    m = _FIRST_P_RE.search(before_table)
    if m:
        text = _plain_answer(m.group(1), max_len=600)
        if text.rstrip().endswith((":", "：")):
            after_p = before_table[m.end() :]
            ul_items = _LI_RE.findall(after_p)
            if ul_items:
                extras = [_plain_answer(item, max_len=120) for item in ul_items[:2]]
                extras = [e for e in extras if e]
                if extras:
                    text = f"{text.rstrip()} {'؛ '.join(extras)}"
        if len(text) >= 25:
            return text

    items = _LI_RE.findall(before_table)
    if items:
        parts = [_plain_answer(item, max_len=220) for item in items[:3]]
        parts = [p for p in parts if p]
        if parts:
            return "؛ ".join(parts)

    text = _plain_answer(before_table, max_len=500)
    if len(text) < 50 and re.search(r"<table\b", src, re.I):
        after_table = re.sub(
            r".*?<table\b[^>]*>.*?</table>",
            "",
            src,
            count=1,
            flags=re.I | re.S,
        )
        ul_items = _LI_RE.findall(after_table)
        if ul_items:
            parts = [_plain_answer(item, max_len=200) for item in ul_items[:2]]
            parts = [p for p in parts if p]
            if parts:
                prefix = f"{text} — " if text else ""
                return prefix + "؛ ".join(parts)

    if len(text) >= 25:
        return text

    m = _FIRST_P_RE.search(src)
    if m:
        text = _plain_answer(m.group(1), max_len=600)
        if text:
            return text

    return _plain_answer(src, max_len=1200)


def _absolute_url(request, path: str, site_url: str) -> str:
    base = (site_url or "").rstrip("/")
    if base:
        return f"{base}{path}"
    return request.build_absolute_uri(path)


def _default_meta(*, institute_name: str, category: Optional[FAQCategory]) -> tuple[str, str]:
    if category:
        return category.get_meta_title(), category.get_meta_description()

    title = "سوالات متداول مهاجرت تحصیلی و اعزام دانشجو"
    description = (
        f"پاسخ کامل سوالات متداول درباره مهاجرت تحصیلی، ویزای تحصیلی، پذیرش دانشگاه، "
        f"بورسیه و اعزام دانشجو — راهنمای {institute_name} برای دانشجویان ایرانی."
    )
    return title, description


def _meta_keywords(
    category: Optional[FAQCategory],
    categories: list[FAQCategory],
) -> str:
    base = [
        "سوالات متداول",
        "مهاجرت تحصیلی",
        "اعزام دانشجو",
        "ویزای تحصیلی",
        "پذیرش دانشگاه",
        "بورسیه تحصیلی",
        "مشاوره مهاجرت",
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
    category: Optional[FAQCategory],
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
            "name": "سوالات متداول",
            "item": page_url if not category else _absolute_url_from_site(site_url, reverse("faq")),
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


def _absolute_url_from_site(site_url: str, path: str) -> str:
    return f"{site_url.rstrip('/')}{path}"


def _faq_detail_url(site_url: str, faq: FAQ) -> str:
    path = reverse("faq_detail", kwargs={"faq_slug": faq.slug})
    return _absolute_url_from_site(site_url, path)


def build_faq_schema(
    *,
    site_url: str,
    page_url: str,
    page_title: str,
    page_description: str,
    institute_name: str,
    faqs: list[FAQ],
    category: Optional[FAQCategory],
    categories: list[FAQCategory],
) -> dict[str, Any]:
    """@graph شامل WebPage، FAQPage، BreadcrumbList و (در صفحه اصلی) ItemList."""
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

    questions: list[dict[str, Any]] = []
    for faq in faqs:
        answer_text = _plain_answer(faq.answer)
        if not answer_text:
            continue
        entry: dict[str, Any] = {
            "@type": "Question",
            "name": faq.question,
            "acceptedAnswer": {
                "@type": "Answer",
                "text": answer_text,
            },
        }
        if faq.slug:
            entry["url"] = _faq_detail_url(site_url, faq)
        questions.append(entry)

    if questions:
        graph.append(
            {
                "@type": "FAQPage",
                "@id": f"{page_url}#faqpage",
                "url": page_url,
                "mainEntity": questions,
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
                "name": "دسته‌بندی سوالات متداول",
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": idx,
                        "name": cat.name,
                        "url": _absolute_url_from_site(
                            site_url,
                            reverse("faq_category", kwargs={"category_slug": cat.slug}),
                        ),
                    }
                    for idx, cat in enumerate(categories, start=1)
                ],
            }
        )

    return {"@context": "https://schema.org", "@graph": graph}


def build_faq_page_seo(
    *,
    request,
    institute_name: str,
    active_category: Optional[FAQCategory],
    categories: list[FAQCategory],
    faqs: list[FAQ],
    site_url: str,
) -> dict[str, Any]:
    """متادیتا و JSON-LD برای قالب faq.html."""
    path = (
        reverse("faq_category", kwargs={"category_slug": active_category.slug})
        if active_category
        else reverse("faq")
    )
    page_url = _absolute_url(request, path, site_url)

    meta_title, meta_description = _default_meta(
        institute_name=institute_name,
        category=active_category,
    )

    page_title_for_schema = meta_title.split("|")[0].strip() if "|" in meta_title else meta_title

    schema = build_faq_schema(
        site_url=site_url,
        page_url=page_url,
        page_title=page_title_for_schema,
        page_description=meta_description,
        institute_name=institute_name,
        faqs=faqs,
        category=active_category,
        categories=categories,
    )

    og_title = f"{meta_title} | {institute_name}" if institute_name else meta_title

    return {
        "faq_meta_title": meta_title,
        "faq_meta_description": meta_description,
        "faq_meta_keywords": _meta_keywords(active_category, categories),
        "faq_page_url": page_url,
        "faq_schema": schema,
        "faq_schema_json": json.dumps(schema, ensure_ascii=False),
        "faq_og_title": og_title,
    }


def _faq_detail_breadcrumbs(
    *,
    site_url: str,
    page_url: str,
    faq: FAQ,
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
            "name": "سوالات متداول",
            "item": _absolute_url_from_site(site_url, reverse("faq")),
        },
    ]
    position = 3
    if faq.category:
        items.append(
            {
                "@type": "ListItem",
                "position": position,
                "name": faq.category.name,
                "item": _absolute_url_from_site(
                    site_url,
                    reverse("faq_category", kwargs={"category_slug": faq.category.slug}),
                ),
            }
        )
        position += 1
    items.append(
        {
            "@type": "ListItem",
            "position": position,
            "name": faq.question,
            "item": page_url,
        }
    )
    return items


def build_faq_detail_page_seo(
    *,
    request,
    faq: FAQ,
    institute_name: str,
    site_url: str,
) -> dict[str, Any]:
    """متادیتا و JSON-LD برای صفحه اختصاصی سوال."""
    path = reverse("faq_detail", kwargs={"faq_slug": faq.slug})
    page_url = _absolute_url(request, path, site_url)
    page_url = page_url.rstrip("/") + "/"

    meta_title = faq.get_meta_title()
    meta_description = faq.get_meta_description()
    og_title = f"{meta_title} | {institute_name}" if institute_name else meta_title

    answer_text = _plain_answer(faq.get_detail_html())
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
            "@type": "QAPage",
            "@id": f"{page_url}#qa",
            "url": page_url,
            "mainEntity": {
                "@type": "Question",
                "name": faq.question,
                "text": faq.question,
                "answerCount": 1,
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": answer_text,
                    "url": page_url,
                },
            },
        },
        {
            "@type": "BreadcrumbList",
            "@id": f"{page_url}#breadcrumb",
            "itemListElement": _faq_detail_breadcrumbs(
                site_url=site_url,
                page_url=page_url,
                faq=faq,
            ),
        },
    ]

    keywords = faq.get_keywords_list()
    if faq.category and faq.category.name not in keywords:
        keywords = [faq.category.name, *keywords]

    return {
        "faq_meta_title": meta_title,
        "faq_meta_description": meta_description,
        "faq_meta_keywords": ", ".join(
            ["سوالات متداول", "مهاجرت تحصیلی", *keywords[:8]]
        ),
        "faq_page_url": page_url,
        "faq_schema": {"@context": "https://schema.org", "@graph": graph},
        "faq_schema_json": json.dumps(
            {"@context": "https://schema.org", "@graph": graph},
            ensure_ascii=False,
        ),
        "faq_og_title": og_title,
    }
