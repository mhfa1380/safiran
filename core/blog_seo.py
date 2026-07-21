"""سئو و سیگنال Google AI برای مقاله وبلاگ."""

from __future__ import annotations

from typing import Any

from django.urls import reverse
from django.utils.html import strip_tags

from .google_ai_seo import augment_blog_posting_schema, build_blog_ai_qa_blocks, build_blog_answer_summary


def build_blog_post_seo(
    *,
    post,
    site_url: str,
    canonical_url: str,
    institute_name: str,
    org_schema_id: str,
    static_logo_path: str,
) -> dict[str, Any]:
    site = site_url.rstrip("/")
    page = (post.canonical_url or canonical_url).rstrip("/") + "/"
    title = post.meta_title or post.title
    description = (
        post.meta_description
        or post.excerpt
        or strip_tags(post.content or "")[:160]
    )

    qa_blocks = build_blog_ai_qa_blocks(post)
    answer_summary = build_blog_answer_summary(post)

    author: dict[str, Any] = {
        "@type": "Person",
        "name": post.author.name,
    }
    if post.author.role:
        author["jobTitle"] = post.author.role
    if post.author.bio:
        author["description"] = post.author.bio
    author["worksFor"] = {
        "@type": "Organization",
        "@id": org_schema_id,
        "name": institute_name,
    }
    if post.author.has_photo:
        photo_url = post.author.photo.url
        if not photo_url.startswith("http"):
            photo_url = f"{site}{photo_url}"
        author["image"] = photo_url

    blog_posting: dict[str, Any] = {
        "@type": "BlogPosting",
        "@id": f"{page}#article",
        "mainEntityOfPage": {"@type": "WebPage", "@id": page},
        "headline": title,
        "description": description[:320],
        "url": page,
        "articleSection": post.country_tag or "وبلاگ",
        "keywords": post.meta_keywords or post.country_tag or "وبلاگ, مهاجرت تحصیلی",
        "inLanguage": "fa-IR",
        "datePublished": post.created_at.isoformat(),
        "dateModified": post.updated_at.isoformat(),
        "author": author,
        "publisher": {
            "@type": "Organization",
            "name": institute_name,
            "logo": {"@type": "ImageObject", "url": f"{site}{static_logo_path}"},
        },
    }
    if post.image:
        image_url = post.image.url
        if not image_url.startswith("http"):
            image_url = f"{site}{image_url}"
        blog_posting["image"] = image_url

    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "BreadcrumbList",
                "@id": f"{page}#breadcrumb",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "صفحه اصلی", "item": f"{site}/"},
                    {
                        "@type": "ListItem",
                        "position": 2,
                        "name": "وبلاگ",
                        "item": f"{site}{reverse('blog')}",
                    },
                    {"@type": "ListItem", "position": 3, "name": title, "item": page},
                ],
            },
            blog_posting,
        ],
    }

    schema_json = augment_blog_posting_schema(
        schema,
        site_url=site,
        qa_blocks=qa_blocks,
    )

    return {
        "blog_ai_qa_blocks": qa_blocks,
        "blog_answer_summary": answer_summary,
        "blog_schema_json": schema_json,
        "blog_ai_qa_title": "خلاصه و نکات کلیدی این مطلب",
        "blog_ai_qa_lead": f"پاسخ کوتاه {institute_name} — برای جزئیات کامل متن مقاله را بخوانید.",
    }
