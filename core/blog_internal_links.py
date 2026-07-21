"""
لینک‌سازی داخلی وبلاگ — در متن مقاله و گروه‌های discovery.
"""
from __future__ import annotations

import hashlib
import re
from html import escape

from django.urls import reverse

from .blog_search import related_blog_posts
from .internal_linking import (
    InternalLink,
    InternalLinkGroup,
    get_blog_resource_groups,
    get_priority_related_majors,
    get_priority_related_universities,
)
from .models import BlogPost
from .study_destinations import PRIMARY_STUDY_COUNTRY_LABELS, WORLD_STUDY_COUNTRY_LABELS

MARKER = "data-blog-internal-links-v1"
_BLOCK_CLASS = "blog-internal-links"

# برچسب فارسی → کد کشور در سایت
_COUNTRY_TAG_TO_CODE: dict[str, str] = {
    **{v: k for k, v in PRIMARY_STUDY_COUNTRY_LABELS.items()},
    **{v: k for k, v in WORLD_STUDY_COUNTRY_LABELS.items()},
    "اروپا": "",
    "مقایسه‌ای": "",
    "آموزشی": "",
    "مشکل‌محور": "",
    "هزینه": "",
    "مهاجرت تحصیلی": "",
    "خدمات موسسه": "",
    "ارزیابی رایگان": "",
    "قوانین و اخبار": "",
    "زندگی دانشجویی": "",
    "غذا و فرهنگ": "",
    "مقایسه کشورها": "",
}

# کلمات در slug برای تشخیص کشور
_SLUG_COUNTRY_HINTS: tuple[tuple[str, str], ...] = (
    ("canada", "canada"),
    ("germany", "germany"),
    ("german", "germany"),
    ("spain", "spain"),
    ("spanish", "spain"),
    ("china", "china"),
    ("chinese", "china"),
    ("csc", "china"),
    ("hsk", "china"),
    ("usa", "usa"),
    ("america", "usa"),
    ("f1", "usa"),
    ("france", "france"),
    ("french", "france"),
    ("netherlands", "netherlands"),
    ("holland", "netherlands"),
    ("italy", "italy"),
    ("sweden", "sweden"),
    ("finland", "finland"),
    ("europe", ""),
)

_TOPIC_ANCHORS: tuple[tuple[tuple[str, ...], str, str], ...] = (
    (("visa", "ویزا", "permit", "gic", "nie", "x1", "f1"), "راهنمای ویزای تحصیلی", "ویزای تحصیلی"),
    (("scholarship", "csc", "بورسیه", "daad", "eiffel"), "مقالات بورسیه", "بورسیه تحصیلی"),
    (("cost", "هزینه", "living", "tuition"), "برآورد هزینه تحصیل", "هزینه تحصیل"),
    (("sop", "motivation", "انگیزه", "resume", "cv"), "آماده‌سازی مدارک اپلای", "مدارک اپلای"),
    (("refusal", "ریجکت", "reject"), "رفع ریجکت ویزا", "ریجکتی ویزا"),
    (("work", "pgwp", "opt", "job"), "کار دانشجویی", "کار در حین تحصیل"),
    (("admission", "apply", "اپلای", "deadline"), "پذیرش دانشگاه", "اپلای دانشگاه"),
)

_STRIP_OLD_BLOCK = re.compile(
    rf'<aside[^>]*{re.escape(_BLOCK_CLASS)}[^>]*>.*?</aside>\s*',
    re.DOTALL | re.IGNORECASE,
)


def country_code_for_post(post: BlogPost) -> str:
    tag = (post.country_tag or "").strip()
    if tag in _COUNTRY_TAG_TO_CODE:
        return _COUNTRY_TAG_TO_CODE[tag]
    slug = post.slug.lower()
    for hint, code in _SLUG_COUNTRY_HINTS:
        if hint and hint in slug:
            return code
    for hint, code in _SLUG_COUNTRY_HINTS:
        if hint and hint in tag.lower():
            return code
    return ""


def _blog_path(slug: str) -> str:
    return reverse("blog_detail", kwargs={"slug": slug})


def _pick_related_posts(post: BlogPost, *, limit: int = 6) -> list[BlogPost]:
    related = related_blog_posts(post, limit=limit + 2)
    out: list[BlogPost] = []
    tag = (post.country_tag or "").strip()
    for p in related:
        if p.pk == post.pk:
            continue
        out.append(p)
        if len(out) >= limit:
            break
    if len(out) < 3 and tag:
        extra = (
            BlogPost.objects.filter(is_published=True, country_tag=tag)
            .exclude(pk=post.pk)
            .exclude(slug__in=[x.slug for x in out])
            .order_by("-created_at")[: limit - len(out)]
        )
        out.extend(list(extra))
    return out[:limit]


def _topic_anchor(slug: str) -> tuple[str, str]:
    s = slug.lower()
    for keys, phrase, short in _TOPIC_ANCHORS:
        if any(k in s for k in keys):
            return phrase, short
    return "مطالب مرتبط مهاجرت تحصیلی", "مهاجرت تحصیلی"


def build_incontent_links_html(post: BlogPost, related: list[BlogPost]) -> str:
    """بلوک HTML لینک‌های داخلی برای داخل مقاله."""
    if not related:
        return ""

    topic_phrase, topic_short = _topic_anchor(post.slug)
    items: list[str] = []
    for rp in related:
        url = _blog_path(rp.slug)
        title = escape(rp.title, quote=True)
        items.append(
            f'<li><a href="{url}" title="{title}">{title}</a></li>'
        )

    country = country_code_for_post(post)
    quick: list[str] = []
    quick.append(
        f'<a href="{reverse("evaluation")}">ارزیابی رایگان مهاجرت تحصیلی</a>'
    )
    if country and country in PRIMARY_STUDY_COUNTRY_LABELS:
        quick.append(
            f'<a href="{reverse("country_detail", kwargs={"country_code": country})}">'
            f'تحصیل در {escape(PRIMARY_STUDY_COUNTRY_LABELS[country], quote=True)}</a>'
        )
    quick.append(f'<a href="{reverse("faq")}">سوالات متداول</a>')
    quick.append(f'<a href="{reverse("blog")}">همه مطالب وبلاگ</a>')

    quick_html = " · ".join(quick)
    return f"""
<aside class="{_BLOCK_CLASS}" {MARKER} aria-label="لینک‌های داخلی پیشنهادی">
<h2>مطالب پیشنهادی: {escape(topic_phrase, quote=True)}</h2>
<p>برای تکمیل مسیر {escape(topic_short, quote=True)}، این مطالب تخصصی {escape(post.country_tag or "موسسه سفیران", quote=True)} را بخوانید:</p>
<ul class="{_BLOCK_CLASS}__list">
{"".join(items)}
</ul>
<p class="{_BLOCK_CLASS}__quick"><strong>صفحات مفید:</strong> {quick_html}</p>
</aside>
"""


def inject_links_into_content(content: str, post: BlogPost) -> str:
    """درج یا جایگزینی بلوک لینک داخلی در HTML مقاله."""
    cleaned = _STRIP_OLD_BLOCK.sub("", content)
    related = _pick_related_posts(post, limit=6)
    block = build_incontent_links_html(post, related)
    if not block.strip():
        return cleaned

    for needle in ("<h2>جمع‌بندی</h2>", "<h2>جمع بندی</h2>"):
        if needle in cleaned:
            return cleaned.replace(needle, block + "\n" + needle, 1)

    if 'class="eval-analyze' in cleaned or "ارزیابی رایگان" in cleaned:
        # قبل از CTA ارزیابی
        idx = cleaned.find("<div style=")
        if idx > 200:
            return cleaned[:idx] + block + cleaned[idx:]

    return cleaned.rstrip() + "\n" + block


def get_enhanced_blog_resource_groups(post: BlogPost) -> list[InternalLinkGroup]:
    """
    گروه لینک برای discovery hub زیر مقاله:
    وبلاگ‌های مرتبط + دانشگاه/رشته + صفحات کلیدی.
    """
    groups: list[InternalLinkGroup] = list(get_blog_resource_groups(post.slug))

    related = _pick_related_posts(post, limit=5)
    if related:
        existing_blog_urls = {
            ln.url for g in groups for ln in g.links if ln.kind == "blog"
        }
        blog_links = tuple(
            InternalLink(label=p.title, url=_blog_path(p.slug), kind="blog")
            for p in related
            if _blog_path(p.slug) not in existing_blog_urls
        )
        if blog_links:
            groups.insert(
                0,
                InternalLinkGroup(
                    title="مطالب مرتبط در وبلاگ",
                    links=blog_links,
                ),
            )

    country = country_code_for_post(post)
    if country:
        unis = get_priority_related_universities(country=country, limit=5)
        if unis:
            from .internal_linking import _uni_links

            groups.append(
                InternalLinkGroup(
                    title=f"دانشگاه‌های {PRIMARY_STUDY_COUNTRY_LABELS.get(country, country)}",
                    links=_uni_links(unis),
                )
            )
        majors = get_priority_related_majors(country=country, limit=5)
        if majors:
            from .internal_linking import _major_links

            groups.append(
                InternalLinkGroup(
                    title="رشته‌های پرطرفدار",
                    links=_major_links(majors),
                )
            )
        if country in PRIMARY_STUDY_COUNTRY_LABELS:
            label = PRIMARY_STUDY_COUNTRY_LABELS[country]
            groups.append(
                InternalLinkGroup(
                    title="صفحات تخصصی",
                    links=(
                        InternalLink(
                            label=f"راهنمای تحصیل در {label}",
                            url=reverse("country_detail", kwargs={"country_code": country}),
                            kind="page",
                        ),
                        InternalLink(
                            label="لیست دانشگاه‌ها",
                            url=reverse("schools_list"),
                            kind="page",
                        ),
                    ),
                )
            )

    # صفحات ثابت سئو
    core = (
        InternalLink("ارزیابی هوشمند رایگان", reverse("evaluation"), "page"),
        InternalLink("مشاوره و خدمات", reverse("services"), "page"),
        InternalLink("رزرو نوبت مشاوره", reverse("appointment"), "page"),
    )
    groups.append(InternalLinkGroup(title="شروع از اینجا", links=core))

    return groups


def stable_minute_offset(slug: str) -> int:
    """پراکندگی دقیقه انتشار بر اساس slug."""
    return int(hashlib.md5(slug.encode()).hexdigest()[:4], 16) % 28
