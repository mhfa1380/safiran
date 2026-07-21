"""
تولید HTML غنی و ورودی کاتالوگ StudyCountry برای کشورهای جهانی.
"""

from __future__ import annotations

from typing import Any

from core.study_destinations import WORLD_STUDY_COUNTRY_LABELS

from .seo_content_shared import COUNTRY_SEO_HOOKS, evaluation_href


def country_media_img(code: str, slot: str, alt: str) -> str:
    """تصویر بخش محتوا — پس از seed در media/countries/ ذخیره می‌شود."""
    src = f"/media/countries/{code}-{slot}.jpg"
    return (
        f'<figure class="country-page__figure">'
        f'<img src="{src}" alt="{alt}" loading="lazy" width="800" height="450">'
        f'<figcaption class="country-page__figure-cap">{alt}</figcaption>'
        f"</figure>"
    )


def _internal_links(code: str, name: str) -> str:
    ev = evaluation_href(code, ref="country-page")
    return (
        f"<h3>گام‌های بعدی در سایت سفیران</h3>"
        f"<ul>"
        f'<li><a href="/رشته-های-تحصیلی/?country={code}">رشته‌های تحصیلی {name}</a></li>'
        f'<li><a href="/دانشگاه-های-خارج/?country={code}">دانشگاه‌های {name}</a></li>'
        f'<li><a href="{ev}">ارزیابی رایگان شرایط پرونده</a></li>'
        f'<li><a href="/کشور/{code}/بورسیه/">راهنمای بورسیه {name}</a></li>'
        f"</ul>"
    )


def _table(headers: list[str], rows: list[tuple[str, ...]]) -> str:
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = ""
    for row in rows:
        body += "<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>"
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _list(items: list[str], *, ordered: bool = False) -> str:
    tag = "ol" if ordered else "ul"
    inner = "".join(f"<li>{item}</li>" for item in items)
    return f"<{tag}>{inner}</{tag}>"


def build_description(facts: dict[str, Any]) -> str:
    code = facts["code"]
    name = facts["name"]
    hook = facts.get("hook", "")
    intl = facts.get("intl_students", "")
    degrees = facts.get("degrees", [])
    cities = facts.get("cities", [])
    popular_fields = facts.get("popular_fields", [])
    lang_note = facts.get("language_note", "")
    extra = facts.get("description_extra", "")

    parts = [
        f"<h2>چرا تحصیل در {name}؟</h2>",
        f"<p>{name} {hook} "
        f"{'بیش از ' + intl + ' دانشجوی بین‌المللی دارد. ' if intl else ''}"
        f"در این راهنما همه‌چیز را ساده و مرحله‌به‌مرحله توضیح می‌دهیم تا بدون سردرگمی "
        f"مسیر پذیرش، ویزا و زندگی دانشجویی را بشناسید.</p>",
        country_media_img(code, "campus", f"محیط دانشگاهی و تحصیل در {name}"),
    ]

    if degrees:
        parts.append("<h3>مقاطع و مدت تحصیل</h3>")
        parts.append(_table(["مقطع", "مدت تقریبی", "یادداشت"], degrees))

    if popular_fields:
        parts.append(f"<h3>رشته‌های پرطرفدار برای ایرانی‌ها</h3>")
        parts.append(_list(popular_fields))

    if cities:
        parts.append("<h3>شهرهای محبوب دانشجویی</h3>")
        parts.append(
            _table(["شهر", "ویژگی"], [(c[0], c[1]) for c in cities])
        )

    if lang_note:
        parts.append("<h3>زبان تحصیل</h3>")
        parts.append(f"<p>{lang_note}</p>")

    if extra:
        parts.append(extra)

    parts.append(
        f"<p>تیم <strong>موسسه سفیران آینده روشن</strong> بر اساس معدل، زبان، بودجه و هدف شغلی شما، "
        f"بهترین دانشگاه و زمان‌بندی اپلای {name} را پیشنهاد می‌دهد.</p>"
    )
    parts.append(_internal_links(code, name))
    return "\n".join(parts)


def build_visa_info(facts: dict[str, Any]) -> str:
    code = facts["code"]
    name = facts["name"]
    visa_name = facts.get("visa_name", "ویزای تحصیلی")
    sections = facts.get("visa_sections", [])
    work = facts.get("work_rights", "")
    post = facts.get("post_study", "")
    finance = facts.get("visa_finance", "")
    official = facts.get("official_visa_url", "")
    extra = facts.get("visa_extra", "")

    parts = [
        f"<h3>{visa_name}</h3>",
        country_media_img(code, "visa", f"مدارک و فرآیند ویزای تحصیلی {name}"),
    ]
    if finance:
        parts.append(f"<p><strong>تمکن مالی ویزا:</strong> {finance}</p>")

    for title, body in sections:
        parts.append(f"<h3>{title}</h3>")
        parts.append(f"<p>{body}</p>" if not body.strip().startswith("<") else body)

    if work:
        parts.append("<h3>حق کار حین تحصیل</h3>")
        parts.append(f"<p>{work}</p>")
    if post:
        parts.append("<h3>اقامت و کار پس از تحصیل</h3>")
        parts.append(f"<p>{post}</p>")
    if extra:
        parts.append(extra)
    if official:
        parts.append(
            f'<p><em>قبل از اپلای، صفحه رسمی '
            f'<a href="{official}" rel="noopener noreferrer" target="_blank">اداره مهاجرت {name}</a> '
            f"را بررسی کنید — مقررات ممکن است تغییر کند.</em></p>"
        )
    return "\n".join(parts)


def build_admission_info(facts: dict[str, Any]) -> str:
    name = facts["name"]
    steps = facts.get("admission_steps", [])
    lang_table = facts.get("lang_requirements", [])
    deadlines = facts.get("deadlines", "")
    docs = facts.get("documents", [])
    extra = facts.get("admission_extra", "")

    parts = [f"<h3>مراحل پذیرش و اپلای در {name}</h3>"]
    if steps:
        parts.append(_list(steps, ordered=True))
    if lang_table:
        parts.append("<h3>شرایط زبان (راهنما)</h3>")
        parts.append(_table(["مقطع / برنامه", "نیاز زبانی"], lang_table))
    if deadlines:
        parts.append("<h3>زمان‌بندی و مهلت‌ها</h3>")
        parts.append(f"<p>{deadlines}</p>")
    if docs:
        parts.append("<h3>مدارک متداول</h3>")
        parts.append(_list(docs))
    if extra:
        parts.append(extra)
    return "\n".join(parts)


def build_living_info(facts: dict[str, Any]) -> str:
    code = facts["code"]
    name = facts["name"]
    living_table = facts.get("living_costs", [])
    tuition = facts.get("tuition", [])
    housing = facts.get("housing_note", "")
    extra = facts.get("living_extra", "")

    parts = [
        f"<h3>هزینه زندگی ماهانه در {name} (تقریبی ۲۰۲۵–۲۰۲۶)</h3>",
        country_media_img(code, "city", f"زندگی دانشجویی در شهرهای {name}"),
    ]
    if living_table:
        cols = len(living_table[0]) if living_table else 2
        headers = ["شهر", "هزینه ماهانه", "یادداشت"][:cols]
        parts.append(_table(headers, living_table))
    if tuition:
        parts.append("<h3>شهریه سالانه (راهنما)</h3>")
        parts.append(_list([f"<strong>{t[0]}:</strong> {t[1]}" for t in tuition]))
    if housing:
        parts.append("<h3>اسکان دانشجویی</h3>")
        parts.append(f"<p>{housing}</p>")
    if extra:
        parts.append(extra)
    return "\n".join(parts)


def build_scholarship_info(facts: dict[str, Any]) -> str:
    code = facts["code"]
    name = facts["name"]
    intro = facts.get("scholarship_intro", "")
    items = facts.get("scholarships", [])
    tips = facts.get("scholarship_tips", "")
    extra = facts.get("scholarship_extra", "")

    parts = [f"<h3>بورسیه و کمک‌هزینه تحصیل در {name}</h3>"]
    if intro:
        parts.append(f"<p>{intro}</p>")
    if items:
        parts.append(_list([f"<strong>{s[0]}:</strong> {s[1]}" for s in items]))
    if tips:
        parts.append(f"<p>{tips}</p>")
    if extra:
        parts.append(extra)
    parts.append(
        f'<p><a href="/کشور/{code}/بورسیه/">مشاهده راهنمای کامل بورسیه {name}</a> '
        f"— شامل مبالغ، مهلت‌ها و لینک رسمی هر برنامه.</p>"
    )
    return "\n".join(parts)


def build_catalog_entry(facts: dict[str, Any], *, order: int) -> dict[str, Any]:
    code = facts["code"]
    name = facts["name"]
    hook_pair = COUNTRY_SEO_HOOKS.get(code, ("پذیرش ۲۰۲۶", "ویزای تحصیلی"))
    headline = facts.get(
        "headline",
        f"تحصیل در {name}؛ راهنمای کامل پذیرش، ویزا و بورسیه برای دانشجویان ایرانی",
    )
    intro = facts.get(
        "intro",
        f"{name} یکی از مقصدهای محبوب تحصیل abroad است: {hook_pair[0]} و {hook_pair[1]}. "
        f"در این صفحه با زبان ساده، از انتخاب رشته تا ویزا و هزینه زندگی را مرور می‌کنید.",
    )

    keywords = facts.get(
        "search_keywords",
        f"{name}, تحصیل {name}, ویزای {name}, دانشگاه {name}, بورسیه {name}, اپلای {name}, {code}",
    )

    return {
        "code": code,
        "name": name,
        "headline": headline,
        "intro": intro,
        "description": build_description(facts),
        "pros": "\n".join(facts.get("pros", [])),
        "cons": "\n".join(facts.get("cons", [])),
        "visa_info": build_visa_info(facts),
        "admission_info": build_admission_info(facts),
        "living_info": build_living_info(facts),
        "scholarship_info": build_scholarship_info(facts),
        "search_keywords": keywords,
        "meta_title": facts.get("meta_title", f"تحصیل در {name} ۲۰۲۶ | راهنمای پذیرش، ویزا و بورسیه"),
        "meta_description": facts.get(
            "meta_description",
            f"راهنمای جامع تحصیل در {name}: دانشگاه‌ها، ویزای تحصیلی، شهریه، "
            f"هزینه زندگی، بورسیه و مشاوره رایگان اپلای — موسسه سفیران.",
        ),
        "meta_keywords": facts.get(
            "meta_keywords",
            f"تحصیل {name}, ویزای {name}, دانشگاه {name}, بورسیه {name}, اپلای {name}",
        ),
        "order": order,
        "is_active": True,
    }


def build_pathway_meta(facts: dict[str, Any]) -> dict[str, Any]:
    """متادیتای مسیر مهاجرت — برای country_immigration_pathway."""
    return {
        "total_duration": facts.get("pathway_duration", "۱۰ تا ۱۸ ماه (از مشاوره تا ورود)"),
        "highlight_stats": tuple(facts.get("pathway_stats", ())),
        "step_details": facts.get("pathway_steps", {}),
    }
