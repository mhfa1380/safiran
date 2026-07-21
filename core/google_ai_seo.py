"""
بهینه‌سازی برای Google AI Overviews و AI Mode.

مطابق راهنمای رسمی Search Central (2025–2026):
- همان ایندکس و رتبه‌بندی جستجوی معمولی
- صفحه باید snippet-eligible باشد (بدون nosnippet / محدودیت شدید)
- محتوای منحصربه‌فرد، ساختار هدینگ روشن، schema هم‌خوان با متن visible
- llms.txt برای گوگل لازم نیست؛ تمرکز این ماژول روی سیگنال‌هایی است که گوگل اعلام کرده مؤثرند
"""
from __future__ import annotations

import json
from typing import Any

from django.urls import reverse

from .faq_seo import _plain_answer, _teaser_plain_from_html

# اجازهٔ snippet کامل — پیش‌نیاز eligibility در AI Overviews
_GOOGLE_SNIPPET_DIRECTIVES = (
    "max-snippet:-1",
    "max-image-preview:large",
    "max-video-preview:-1",
)


def enrich_robots_for_google_ai(robots: str) -> str:
    """به robots index,follow دستورات snippet گوگل را اضافه می‌کند."""
    directive = (robots or "index, follow").strip()
    if "noindex" in directive:
        return directive
    parts = [p.strip() for p in directive.split(",") if p.strip()]
    existing = {p.split(":")[0].strip() for p in parts if ":" in p}
    for extra in _GOOGLE_SNIPPET_DIRECTIVES:
        key = extra.split(":")[0]
        if key not in existing:
            parts.append(extra)
    return ", ".join(parts)


def get_homepage_featured_faqs(*, limit: int = 6):
    from .models import FAQ

    qs = FAQ.objects.filter(is_active=True, is_featured=True).order_by("order", "id")
    faqs = list(qs[:limit])
    if len(faqs) < 3:
        extra = list(
            FAQ.objects.filter(is_active=True)
            .exclude(pk__in=[f.pk for f in faqs])
            .order_by("order", "id")[: max(0, limit - len(faqs))]
        )
        faqs.extend(extra)
    return faqs[:limit]


def build_index_answer_summary(institute) -> str:
    """پاسخ کوتاه و self-contained برای استخراج AI — زیر h1 صفحه اصلی."""
    name = getattr(institute, "name", "") or "موسسه سفیران آینده روشن"
    city = getattr(institute, "city", "") or "بابل"
    students = int(getattr(institute, "students_sent", 0) or 0)
    countries = int(getattr(institute, "countries_count", 0) or 0)
    return (
        f"{name} موسسهٔ رسمی اعزام دانشجو با مجوز وزارت علوم است که از سال ۱۳۸۹ در {city} "
        f"مشاوره مهاجرت تحصیلی، پذیرش دانشگاه، بورسیه و ویزای تحصیلی برای دانشجویان ایرانی "
        f"ارائه می‌دهد. تاکنون بیش از {students} دانشجو به بیش از {countries} کشور مقصد اعزام شده‌اند."
    )


def build_index_page_schema_json(
    *,
    site_url: str,
    page_url: str,
    institute_name: str,
    answer_summary: str,
    featured_faqs,
) -> str:
    """WebPage + Speakable + FAQPage — فقط برای صفحه اصلی با FAQ visible."""
    site = site_url.rstrip("/")
    page = page_url.rstrip("/") + "/"

    graph: list[dict[str, Any]] = [
        {
            "@type": "WebPage",
            "@id": f"{page}#webpage",
            "url": page,
            "name": f"{institute_name} | مشاوره مهاجرت تحصیلی",
            "description": answer_summary,
            "inLanguage": "fa-IR",
            "isPartOf": {"@id": f"{site}/#website"},
            "about": {"@id": f"{site}/#organization"},
            "speakable": {
                "@type": "SpeakableSpecification",
                "cssSelector": [".index-hero__answer", ".index-ai-faq__answer"],
            },
        }
    ]

    questions: list[dict[str, Any]] = []
    for faq in featured_faqs:
        answer = _plain_answer(faq.answer, max_len=500)
        if not answer:
            continue
        entry: dict[str, Any] = {
            "@type": "Question",
            "name": faq.question,
            "acceptedAnswer": {"@type": "Answer", "text": answer},
        }
        if faq.slug:
            entry["url"] = f"{site}{reverse('faq_detail', kwargs={'faq_slug': faq.slug})}"
        questions.append(entry)

    if questions:
        graph.append(
            {
                "@type": "FAQPage",
                "@id": f"{page}#faq",
                "url": page,
                "mainEntity": questions,
            }
        )

    return json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False)


def _truncate_words(text: str, max_words: int = 55) -> str:
    words = (text or "").split()
    if len(words) <= max_words:
        return " ".join(words)
    return " ".join(words[:max_words]).rstrip("،,.").strip() + "…"


def build_country_ai_qa_blocks(country) -> list[dict[str, str]]:
    """بلوک‌های سوال + پاسخ کوتاه برای استخراج Google AI — هم‌خوان با schema."""
    name = country.name
    blocks: list[dict[str, str]] = []

    intro_src = _plain_answer(country.intro or country.headline or "", max_len=1200)
    if intro_src:
        blocks.append(
            {
                "question": f"تحصیل در {name} برای دانشجویان ایرانی چگونه است؟",
                "short_answer": _truncate_words(intro_src, 52),
                "anchor": "country-intro",
                "anchor_tpl": "country_intro",
            }
        )

    sections = (
        ("visa_info", f"ویزای تحصیلی {name} چه شرایطی دارد؟", "guide-visa", "guide_visa"),
        ("admission_info", f"پذیرش دانشگاه در {name} چگونه است؟", "guide-admission", "guide_admission"),
        ("living_info", f"هزینه زندگی دانشجویی در {name} چقدر است؟", "guide-living", "guide_living"),
        ("scholarship_info", f"بورسیه تحصیلی {name} برای ایرانی‌ها چگونه است؟", "guide-scholarship", "guide_scholarship"),
    )
    for field, question, anchor, anchor_tpl in sections:
        raw = getattr(country, field, "") or ""
        plain = _plain_answer(raw, max_len=1200)
        if not plain:
            continue
        teaser_plain = _teaser_plain_from_html(raw)
        short_answer = _truncate_words(teaser_plain, 52)
        blocks.append(
            {
                "question": question,
                "short_answer": short_answer,
                "anchor": anchor,
                "anchor_tpl": anchor_tpl,
                # وقتی خلاصه با متن کامل یکی است، در آکاردئون تکرار نشود.
                "show_guide_teaser": (
                    short_answer.rstrip("…").strip() != plain.strip()
                    and short_answer.rstrip("…").strip() != teaser_plain.strip()
                ),
            }
        )

    pros = [ln.strip() for ln in (country.pros or "").splitlines() if ln.strip()]
    if pros:
        blocks.append(
            {
                "question": f"مزایای تحصیل در {name} چیست؟",
                "short_answer": _truncate_words("؛ ".join(pros[:4]), 48),
                "anchor": "country-pros",
                "anchor_tpl": "country_pros",
            }
        )

    return blocks


def _faq_entities_from_blocks(blocks: list[dict[str, str]]) -> list[dict[str, Any]]:
    return [
        {
            "@type": "Question",
            "name": b["question"],
            "acceptedAnswer": {"@type": "Answer", "text": b["short_answer"]},
        }
        for b in blocks
        if b.get("question") and b.get("short_answer")
    ]


def build_country_schema_json(
    *,
    country,
    page_url: str,
    institute_name: str,
    site_url: str,
    meta_title: str,
    meta_description: str,
    qa_blocks: list[dict[str, str]],
) -> str:
    """گراف schema کشور — WebPage، Speakable، FAQPage هم‌خوان با محتوای visible."""
    site = site_url.rstrip("/")
    page = page_url.rstrip("/") + "/"

    web_page: dict[str, Any] = {
        "@type": "WebPage",
        "@id": f"{page}#webpage",
        "url": page,
        "name": meta_title,
        "description": meta_description,
        "inLanguage": "fa-IR",
        "about": {"@type": "Country", "name": country.name},
        "publisher": {"@id": f"{site}/#organization"},
        "isPartOf": {"@id": f"{site}/#website"},
        "speakable": {
            "@type": "SpeakableSpecification",
            "cssSelector": [
                ".country-page__intro-text",
                ".country-page__qa-answer",
                ".country-page__guide-answer",
            ],
        },
    }
    intro_plain = _plain_answer(country.intro or country.headline or "", max_len=320)
    if intro_plain:
        web_page["abstract"] = intro_plain

    graph: list[dict[str, Any]] = [
        {
            "@type": "BreadcrumbList",
            "@id": f"{page}#breadcrumb",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "صفحه اصلی", "item": f"{site}/"},
                {"@type": "ListItem", "position": 2, "name": country.name, "item": page},
            ],
        },
        web_page,
    ]

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

    return json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False)


def build_eval_answer_summary() -> str:
    """پاسخ کوتاه self-contained برای صفحه ارزیابی."""
    return (
        "ارزیابی رایگان مهاجرت تحصیلی فرم آنلاینی است که در چند دقیقه شرایط تحصیلی، "
        "زبان و کشور مقصد شما را تحلیل می‌کند و گزارش شخصی‌سازی‌شده‌ای از شانس پذیرش "
        "دانشگاه، بورسیه و برآورد هزینه — بدون پرداخت — ارائه می‌دهد."
    )


def augment_evaluation_schema(schema: dict[str, Any], *, site_url: str) -> str:
    """Speakable و publisher برای صفحه ارزیابی."""
    site = site_url.rstrip("/")
    site_graph = schema.get("@graph", [])
    for node in site_graph:
        if node.get("@type") == "WebPage":
            node["speakable"] = {
                "@type": "SpeakableSpecification",
                "cssSelector": [".eval-answer-summary", ".eval-seo__faq-answer"],
            }
            node["publisher"] = {"@id": f"{site}/#organization"}
            break
    return json.dumps(schema, ensure_ascii=False)


def _is_web_page_node(node: dict[str, Any]) -> bool:
    node_type = node.get("@type")
    if node_type == "WebPage":
        return True
    return isinstance(node_type, list) and "WebPage" in node_type


def enrich_schema_graph_for_google_ai(
    schema: dict[str, Any],
    *,
    site_url: str,
    qa_blocks: list[dict[str, str]],
    speakable_selectors: list[str],
    page_url: str | None = None,
) -> str:
    """Speakable، publisher و FAQPage هم‌خوان با بلوک‌های Q&A visible."""
    site = site_url.rstrip("/")
    graph = list(schema.get("@graph", []))
    resolved_page = (page_url or "").rstrip("/")

    for node in graph:
        if _is_web_page_node(node):
            resolved_page = resolved_page or (node.get("url") or "").rstrip("/")
            node["publisher"] = {"@id": f"{site}/#organization"}
            node["speakable"] = {
                "@type": "SpeakableSpecification",
                "cssSelector": speakable_selectors,
            }
            break

    faq_entities = _faq_entities_from_blocks(qa_blocks)
    if faq_entities and resolved_page:
        page = resolved_page + "/"
        graph.append(
            {
                "@type": "FAQPage",
                "@id": f"{page}#faq",
                "url": page,
                "mainEntity": faq_entities,
            }
        )

    return json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False)


def build_major_ai_qa_blocks(major, major_faqs=None) -> list[dict[str, str]]:
    """بلوک Q&A کوتاه برای صفحه رشته."""
    from .seed_data.rich_content import build_major_summary_answer

    title = major.title
    country_label = major.get_country_display() if major.country else ""
    country_code = major.country or ""
    blocks: list[dict[str, str]] = []

    summary = build_major_summary_answer(title, country_code, country_label)
    if summary:
        question = f"تحصیل {title}"
        if country_label:
            question += f" در {country_label}"
        question += " برای دانشجویان ایرانی چگونه است؟"
        blocks.append(
            {
                "question": question,
                "short_answer": _truncate_words(summary, 52),
                "anchor": "major-intro",
            }
        )

    for idx, faq in enumerate(major_faqs or [], start=1):
        ans_plain = _plain_answer(faq.answer, max_len=800)
        if faq.question and ans_plain:
            blocks.append(
                {
                    "question": faq.question,
                    "short_answer": _truncate_words(ans_plain, 52),
                    "anchor": f"major-faq-{idx}",
                }
            )
    return blocks


def build_university_ai_qa_blocks(university, university_faqs=None) -> list[dict[str, str]]:
    """بلوک Q&A کوتاه برای صفحه دانشگاه."""
    name = university.name_fa
    blocks: list[dict[str, str]] = []

    intro_plain = _plain_answer(university.short_description or university.description, max_len=1200)
    full_desc_plain = _plain_answer(university.description, max_len=80)
    if intro_plain:
        blocks.append(
            {
                "question": f"دانشگاه {name} برای دانشجویان ایرانی مناسب است؟",
                "short_answer": _truncate_words(intro_plain, 52),
                "anchor": "school-about" if full_desc_plain else "school-intro",
            }
        )

    if university.world_rank:
        city = university.city or ""
        country = university.get_country_display() if university.country else ""
        location = "، ".join(part for part in (city, country) if part)
        blocks.append(
            {
                "question": f"رتبه جهانی {name} چقدر است؟",
                "short_answer": (
                    f"دانشگاه {university.name_en or name}"
                    f"{f' در {location}' if location else ''} "
                    f"رتبه جهانی {university.world_rank} دارد."
                ),
                "anchor": "school-rank",
            }
        )

    for idx, faq in enumerate(university_faqs or [], start=1):
        ans_plain = _plain_answer(faq.answer, max_len=800)
        if faq.question and ans_plain:
            blocks.append(
                {
                    "question": faq.question,
                    "short_answer": _truncate_words(ans_plain, 52),
                    "anchor": f"school-faq-{idx}",
                }
            )
    return blocks


def build_services_ai_qa_blocks(
    *,
    institute_name: str,
    category,
    services,
    categories,
) -> list[dict[str, str]]:
    """بلوک Q&A کوتاه برای صفحه خدمات."""
    blocks: list[dict[str, str]] = []

    if category:
        desc = _plain_answer(
            getattr(category, "description", "") or category.get_meta_description(),
            max_len=800,
        )
        blocks.append(
            {
                "question": f"خدمات {category.name} در {institute_name} چیست؟",
                "short_answer": _truncate_words(
                    desc or f"مجموعه خدمات {category.name} برای مهاجرت تحصیلی و اعزام دانشجو.",
                    50,
                ),
                "anchor": "",
            }
        )
    else:
        blocks.append(
            {
                "question": f"خدمات مهاجرت تحصیلی {institute_name} شامل چه مواردی است؟",
                "short_answer": (
                    f"{institute_name} از مشاوره و ارزیابی رایگان تا پذیرش دانشگاه، "
                    "ویزای تحصیلی، بورسیه و استقرار در کشور مقصد همراهی می‌کند."
                ),
                "anchor": "",
            }
        )
        cat_names = [c.name for c in (categories or [])[:4] if c.name]
        if cat_names:
            blocks.append(
                {
                    "question": f"دسته‌بندی خدمات {institute_name} چیست؟",
                    "short_answer": "، ".join(cat_names) + " و سایر خدمات تخصصی مهاجرت تحصیلی.",
                    "anchor": "",
                }
            )

    for svc in services[:5]:
        summary = _plain_answer(svc.get_display_summary(), max_len=600)
        if not summary:
            continue
        anchor = f"service-{svc.slug}" if svc.slug else ""
        blocks.append(
            {
                "question": f"{svc.title} — {institute_name}",
                "short_answer": _truncate_words(summary, 48),
                "anchor": anchor,
            }
        )
    return blocks


def build_pricing_ai_qa_blocks(institute_name: str) -> list[dict[str, str]]:
    """سوالات ثابت تعرفه — هم‌خوان با بخش ماشین‌حساب."""
    return [
        {
            "question": "تعرفه خدمات مهاجرت تحصیلی چگونه محاسبه می‌شود؟",
            "short_answer": (
                f"تعرفه‌ها در {institute_name} بر اساس نوع خدمت (اپلای، ویزا، گواهی مقرری و …) "
                "و شرایط پرونده شما تعیین می‌شود؛ ماشین‌حساب هوشمند صفحه تعرفه برآورد اولیه ارائه می‌دهد."
            ),
            "anchor": "pricing-calculator",
        },
        {
            "question": "ماشین‌حساب تعرفه چه کاری انجام می‌دهد؟",
            "short_answer": (
                "با پاسخ به چند سؤال کوتاه درباره کشور مقصد، مقطع و خدمات موردنیاز، "
                "لیست تعرفه‌های مرتبط و برآورد هزینه پرونده نمایش داده می‌شود."
            ),
            "anchor": "pricing-calculator",
        },
        {
            "question": "آیا مشاوره اولیه رایگان است؟",
            "short_answer": (
                f"ارزیابی آنلاین رایگان و جلسه مشاوره اولیه در {institute_name} "
                "برای آشنایی با مسیر مهاجرت تحصیلی در دسترس است."
            ),
            "anchor": "pricing-calculator",
        },
    ]


def build_about_ai_qa_blocks(institute) -> list[dict[str, str]]:
    """بلوک Q&A برای صفحه درباره ما."""
    name = getattr(institute, "name", "") or "موسسه سفیران آینده روشن"
    city = getattr(institute, "city", "") or "بابل"
    license_date = getattr(institute, "license_issue_date", "") or ""
    students = int(getattr(institute, "students_sent", 0) or 0)

    blocks: list[dict[str, str]] = [
        {
            "question": f"{name} چیست؟",
            "short_answer": build_index_answer_summary(institute),
            "anchor": "about-intro",
        },
        {
            "question": f"آیا {name} مجوز رسمی دارد؟",
            "short_answer": (
                f"بله. {name} با مجوز رسمی وزارت علوم"
                f"{f' (صدور: {license_date})' if license_date else ''} "
                f"در {city} فعالیت می‌کند."
            ),
            "anchor": "about-intro",
        },
        {
            "question": f"خدمات {name} شامل چه مواردی است؟",
            "short_answer": (
                "مشاوره مهاجرت تحصیلی، ارزیابی رایگان، پذیرش دانشگاه، "
                "ویزای تحصیلی، بورسیه و استقرار در کشور مقصد."
            ),
            "anchor": "about-intro",
        },
    ]
    if students:
        blocks.append(
            {
                "question": f"چند دانشجو توسط {name} اعزام شده است؟",
                "short_answer": f"بیش از {students} دانشجو تا کنون از طریق {name} به کشورهای مختلف اعزام شده‌اند.",
                "anchor": "about-stats",
            }
        )
    return blocks


def build_blog_answer_summary(post) -> str:
    """خلاصه self-contained برای بالای مقاله وبلاگ."""
    excerpt = post.meta_description or post.excerpt or _plain_answer(post.content, max_len=400)
    return _truncate_words(excerpt, 55)


def build_blog_ai_qa_blocks(post) -> list[dict[str, str]]:
    """بلوک Q&A کوتاه برای مقاله وبلاگ."""
    summary = build_blog_answer_summary(post)
    blocks: list[dict[str, str]] = [
        {
            "question": f"خلاصه مطلب «{post.title}»",
            "short_answer": summary,
            "anchor": "blog-summary",
        }
    ]
    if post.country_tag:
        blocks.append(
            {
                "question": "این مطلب درباره چه کشور یا موضوعی است؟",
                "short_answer": f"این مقاله درباره {post.country_tag} و مهاجرت تحصیلی منتشر شده است.",
                "anchor": "blog-summary",
            }
        )
    return blocks


def build_scholarship_ai_qa_blocks(
    country,
    guide,
    scholarships,
    *,
    institute_name: str = "",
) -> list[dict[str, str]]:
    """بلوک Q&A کوتاه برای صفحه بورسیه کشور."""
    name = country.name
    blocks: list[dict[str, str]] = []

    intro_plain = _plain_answer(guide.intro, max_len=800)
    if intro_plain:
        blocks.append(
            {
                "question": f"بورسیه تحصیلی {name} برای ایرانی‌ها چگونه است؟",
                "short_answer": _truncate_words(intro_plain, 52),
                "anchor": "scholar-intro",
            }
        )

    overview_teaser = _teaser_plain_from_html(guide.overview or "")
    if overview_teaser:
        blocks.append(
            {
                "question": f"انواع بورسیه {name} چیست؟",
                "short_answer": _truncate_words(overview_teaser, 52),
                "anchor": "scholar-intro",
            }
        )

    app_teaser = _teaser_plain_from_html(guide.application_guide or "")
    if app_teaser:
        blocks.append(
            {
                "question": f"چگونه برای بورسیه {name} اپلای کنیم؟",
                "short_answer": _truncate_words(app_teaser, 52),
                "anchor": "scholar-apply",
            }
        )

    if scholarships:
        blocks.append(
            {
                "question": f"چند برنامه بورسیه در {name} معرفی شده است؟",
                "short_answer": (
                    f"در راهنمای بورسیه {name}"
                    f"{f' ({guide.get_degree_label()})' if guide.get_degree_label() else ''} "
                    f"{len(scholarships)} برنامه بورسیه فعال"
                    f"{f' توسط {institute_name}' if institute_name else ''} معرفی شده است."
                ),
                "anchor": "scholar-programs",
            }
        )

    for scholarship in scholarships[:4]:
        if not scholarship.name:
            continue
        detail = scholarship.coverage or ""
        if scholarship.eligibility:
            elig = _plain_answer(scholarship.eligibility, max_len=200)
            if elig:
                detail = f"{detail} — {elig}" if detail else elig
        if not detail:
            continue
        blocks.append(
            {
                "question": f"بورسیه {scholarship.name} در {name} چه پوششی دارد؟",
                "short_answer": _truncate_words(
                    f"{scholarship.provider}: {detail}" if scholarship.provider else detail,
                    48,
                ),
                "anchor": f"scholarship-{scholarship.slug}",
            }
        )

    return blocks


def augment_blog_posting_schema(
    schema: dict[str, Any],
    *,
    site_url: str,
    qa_blocks: list[dict[str, str]],
) -> str:
    """Speakable و FAQPage برای مقاله وبلاگ."""
    site = site_url.rstrip("/")
    graph = list(schema.get("@graph", []))
    page_url = ""

    for node in graph:
        if node.get("@type") == "BlogPosting":
            page_url = (node.get("url") or "").rstrip("/")
            node["speakable"] = {
                "@type": "SpeakableSpecification",
                "cssSelector": [".blog-detail__answer-summary", ".ai-qa-section__answer"],
            }
            node["publisher"] = {
                "@type": "Organization",
                "@id": f"{site}/#organization",
                "name": node.get("publisher", {}).get("name", ""),
            }
            break

    faq_entities = _faq_entities_from_blocks(qa_blocks)
    if faq_entities and page_url:
        page = page_url + "/"
        graph.append(
            {
                "@type": "FAQPage",
                "@id": f"{page}#faq",
                "url": page,
                "mainEntity": faq_entities,
            }
        )

    return json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False)
